package com.swa.backend.engine.executor;

import com.googlecode.aviator.AviatorEvaluator;
import com.googlecode.aviator.AviatorEvaluatorInstance;
import com.googlecode.aviator.Feature;
import com.googlecode.aviator.Options;
import com.swa.backend.common.BizException;
import com.swa.backend.common.ErrorCode;
import org.springframework.stereotype.Component;

import java.util.EnumSet;
import java.util.Map;
import java.util.Set;

/**
 * 条件分支执行器（BE-4.5）：Aviator 求值 config.expression，输出 {"branch": bool}。
 * 引擎据 branch 选择出边。非重试：表达式错误属配置错误，重试无意义。
 * 沙箱口径（SEC-01 修复，与 CodeNodeExecutor 一致）：独立实例 + FEATURE_SET=noneOf + ALLOWED_CLASS_SET=空，
 * 禁止反射调用任意 Java 类方法，防止 DSL 表达式注入。
 */
@Component
public class ConditionNodeExecutor implements NodeExecutor {

    private final AviatorEvaluatorInstance sandbox;

    public ConditionNodeExecutor() {
        this.sandbox = AviatorEvaluator.newInstance();
        this.sandbox.setOption(Options.FEATURE_SET, EnumSet.noneOf(Feature.class));
        this.sandbox.setOption(Options.ALLOWED_CLASS_SET, Set.of());
    }

    @Override
    public String type() {
        return "condition";
    }

    @Override
    public boolean retryable() {
        return false;
    }

    @Override
    public NodeResult execute(NodeContext ctx) {
        String expression = configString(ctx, "expression");
        Object value;
        try {
            sandbox.validate(expression);
            value = sandbox.execute(expression, ctx.getInput());
        } catch (Exception e) {
            throw new BizException(ErrorCode.NODE_EXECUTION_FAILED,
                    "条件表达式求值失败: " + e.getMessage());
        }
        boolean branch = value instanceof Boolean b ? b : Boolean.parseBoolean(String.valueOf(value));
        return NodeResult.ok(Map.of("branch", branch));
    }

    static String configString(NodeContext ctx, String key) {
        Object v = ctx.getNode().getConfig() == null ? null : ctx.getNode().getConfig().get(key);
        if (v == null || String.valueOf(v).isBlank()) {
            throw new BizException(ErrorCode.DSL_INVALID,
                    "节点 " + ctx.getNode().getId() + " 缺少 config." + key);
        }
        return String.valueOf(v);
    }
}
