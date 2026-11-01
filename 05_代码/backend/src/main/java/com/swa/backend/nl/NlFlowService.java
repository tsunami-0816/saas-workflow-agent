package com.swa.backend.nl;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.swa.backend.common.BizException;
import com.swa.backend.common.ErrorCode;
import com.swa.backend.common.TenantContext;
import com.swa.backend.dto.LlmChatRequest;
import com.swa.backend.dto.NlDraftRequest;
import com.swa.backend.dto.WorkflowCreateRequest;
import com.swa.backend.engine.dsl.DslValidator;
import com.swa.backend.entity.FlowTemplate;
import com.swa.backend.entity.Workflow;
import com.swa.backend.entity.WorkflowVersion;
import com.swa.backend.llm.LlmRouterService;
import com.swa.backend.mapper.FlowTemplateMapper;
import com.swa.backend.service.WorkflowService;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * NL→流程草稿（BE-8）：few-shot prompt → 模型路由层(taskType=nl2flow) 生成 DSL JSON
 * → 剥离 markdown 围栏 → DslValidator 校验 → 失败带错重试 1 次 → 建 workflow + 存 draft 版本。
 */
@Service
public class NlFlowService {

    /** few-shot prompt 模板（__REQ__ 为用户需求占位符）。 */
    private static final String PROMPT_TEMPLATE = """
            你是工作流编排助手。把用户需求转成流程 DSL，只输出 JSON，不要 markdown 围栏、不要解释。

            DSL Schema：
            {"nodes":[{"id":"n1","type":"...","name":"...","config":{...}}],
             "edges":[{"source":"n1","target":"n2","branch":null}]}

            规则：
            1. 节点类型仅允许：mqtt-trigger / http / condition / code / delay / agent
            2. mqtt-trigger 是流程起点，不允许有入边；condition 必须同时有 branch="true" 和 branch="false" 两条出边
            3. http 节点 config: {"url":"...","method":"GET或POST","headers":{},"bodyTemplate":"可选，支持 {{上游节点id.字段}} 模板","timeoutMs":10000}
            4. condition 节点 config: {"expression":"Aviator 表达式，引用上游输出如 n1.status > 200"}
            5. code 节点 config: {"expression":"Aviator 纯表达式"}；delay 节点 config: {"delayMs":毫秒数}
            6. agent 节点 config: {"task":"自然语言任务描述","constraints":{}}

            示例1：
            需求：调用汇率接口查询最新汇率
            输出：{"nodes":[{"id":"n1","type":"http","name":"查询汇率","config":{"url":"https://example.com/rate","method":"GET","timeoutMs":10000}}],"edges":[]}

            示例2：
            需求：收到设备温度消息后，温度大于80度时调用告警接口，否则记录温度
            输出：{"nodes":[{"id":"t1","type":"mqtt-trigger","name":"温度消息","config":{}},{"id":"c1","type":"condition","name":"超温判断","config":{"expression":"t1.payload.temp > 80"}},{"id":"h1","type":"http","name":"告警","config":{"url":"https://example.com/alarm","method":"POST","bodyTemplate":"{\\"temp\\":\\"{{t1.payload.temp}}\\"}","timeoutMs":10000}},{"id":"d1","type":"code","name":"记录温度","config":{"expression":"t1.payload.temp"}}],"edges":[{"source":"t1","target":"c1"},{"source":"c1","target":"h1","branch":"true"},{"source":"c1","target":"d1","branch":"false"}]}

            需求：__REQ__
            输出：""";

    private final LlmRouterService llmRouterService;
    private final DslValidator dslValidator;
    private final WorkflowService workflowService;
    private final FlowTemplateMapper flowTemplateMapper;

    public NlFlowService(LlmRouterService llmRouterService, DslValidator dslValidator,
                         WorkflowService workflowService, FlowTemplateMapper flowTemplateMapper) {
        this.llmRouterService = llmRouterService;
        this.dslValidator = dslValidator;
        this.workflowService = workflowService;
        this.flowTemplateMapper = flowTemplateMapper;
    }

    /**
     * 生成流程草稿版本（draft）。
     *
     * @param request 自然语言需求 + 可选流程名
     * @return 新建的 draft 版本
     */
    public WorkflowVersion generateDraft(NlDraftRequest request) {
        String prompt = buildPrompt(request.text());
        GenResult result = generateAndValidate(prompt, null);
        if (result.dsl() == null) {
            // 带错重试 1 次
            result = generateAndValidate(prompt, result.error());
        }
        if (result.dsl() == null) {
            throw new BizException(ErrorCode.NL_GENERATE_FAILED, result.error());
        }

        String name = request.workflowName() != null && !request.workflowName().isBlank()
                ? request.workflowName()
                : "NL流程-" + System.currentTimeMillis();
        Workflow workflow = workflowService.createWorkflow(
                new WorkflowCreateRequest(name, "NL 生成: " + abbreviate(request.text())));
        return workflowService.saveVersion(workflow.getId(), result.dsl());
    }

    /**
     * 组装 prompt：few-shot 模板 + R1 降级模板检索（MySQL flow_template like）。
     */
    private String buildPrompt(String userText) {
        String prompt = PROMPT_TEMPLATE.replace("__REQ__", userText);
        String refs = searchTemplates(userText);
        if (!refs.isBlank()) {
            prompt = prompt + "\n\n参考历史模板（按相似度排序，可借鉴结构但不要照抄）：\n" + refs;
        }
        return prompt;
    }

    /**
     * R1 降级实现：Qdrant 向量检索不可用，改用 MySQL flow_template.summary like 关键词匹配。
     * 取该租户下最近 3 条匹配模板；无匹配则返回空串（不阻塞主流程）。
     */
    private String searchTemplates(String userText) {
        Long tenantId = TenantContext.getTenantId();
        if (tenantId == null) {
            return "";
        }
        // 按标点/空白切词，取长度≥2 的词做 like
        String[] keywords = userText.split("[\\s，。、；：！？,.!?;:()（）]+");
        List<FlowTemplate> matched = new ArrayList<>();
        for (String kw : keywords) {
            if (kw.length() < 2) continue;
            List<FlowTemplate> hits = flowTemplateMapper.selectList(
                    new QueryWrapper<FlowTemplate>()
                            .eq("tenant_id", tenantId)
                            .like("summary", kw)
                            .orderByDesc("updated_at")
                            .last("limit 3"));
            for (FlowTemplate t : hits) {
                if (matched.size() >= 3) break;
                if (matched.stream().noneMatch(m -> m.getId().equals(t.getId()))) {
                    matched.add(t);
                }
            }
            if (matched.size() >= 3) break;
        }
        if (matched.isEmpty()) {
            return "";
        }
        return matched.stream()
                .map(t -> "- " + t.getSummary())
                .collect(Collectors.joining("\n"));
    }

    private record GenResult(String dsl, String error) {
    }

    /**
     * 生成 + 剥离围栏 + 校验；成功返回 dsl，失败返回 error。
     */
    private GenResult generateAndValidate(String prompt, String previousError) {
        String finalPrompt = previousError == null ? prompt
                : prompt + "\n\n上次生成校验失败：" + previousError + "，请修正后重新输出。";
        String content = llmRouterService.chat(new LlmChatRequest(
                "nl2flow", List.of(Map.of("role", "user", "content", finalPrompt)), null)).content();
        String dsl = stripFence(content);
        try {
            dslValidator.validate(dsl);
            return new GenResult(dsl, null);
        } catch (BizException e) {
            return new GenResult(null, e.getMessage());
        }
    }

    /**
     * 剥离 ```json / ``` markdown 围栏。
     */
    static String stripFence(String content) {
        String text = content.trim();
        if (text.startsWith("```")) {
            int firstNewline = text.indexOf('\n');
            text = firstNewline > 0 ? text.substring(firstNewline + 1) : text;
        }
        if (text.endsWith("```")) {
            text = text.substring(0, text.length() - 3);
        }
        return text.trim();
    }

    private static String abbreviate(String text) {
        return text.length() <= 200 ? text : text.substring(0, 200);
    }
}
