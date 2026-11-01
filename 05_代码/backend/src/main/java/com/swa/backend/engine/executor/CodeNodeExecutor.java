package com.swa.backend.engine.executor;

import com.googlecode.aviator.AviatorEvaluatorInstance;
import com.googlecode.aviator.AviatorEvaluator;
import com.googlecode.aviator.Feature;
import com.googlecode.aviator.Options;
import com.swa.backend.common.BizException;
import com.swa.backend.common.ErrorCode;
import org.springframework.stereotype.Component;

import java.util.EnumSet;
import java.util.Map;
import java.util.Set;

/**
 * 代码块执行器（BE-4.6）：Aviator 沙箱求值 config.expression，输出 {"result": 值}。
 * 沙箱口径：独立 AviatorEvaluatorInstance，FEATURE_SET=noneOf（禁用赋值/循环/函数定义等全部特性，
 * 仅允许纯表达式）+ ALLOWED_CLASS_SET=空（禁止反射调用任意 Java 类方法）。
 * 非重试：表达式错误属配置错误。
 */
@Component
public class CodeNodeExecutor implements NodeExecutor {

    private final AviatorEvaluatorInstance sandbox;

    public CodeNodeExecutor() {
        this.sandbox = AviatorEvaluator.newInstance();
        this.sandbox.setOption(Options.FEATURE_SET, EnumSet.noneOf(Feature.class));
        this.sandbox.setOption(Options.ALLOWED_CLASS_SET, Set.of());
    }

    @Override
    public String type() {
        return "code";
    }

    @Override
    public boolean retryable() {
        return false;
    }

    @Override
    public NodeResult execute(NodeContext ctx) {
        String expression = ConditionNodeExecutor.configString(ctx, "expression");
        try {
            sandbox.validate(expression);
            Object value = sandbox.execute(expression, ctx.getInput());
            return NodeResult.ok(Map.of("result", value == null ? "" : value));
        } catch (BizException e) {
            throw e;
        } catch (Exception e) {
            throw new BizException(ErrorCode.NODE_EXECUTION_FAILED,
                    "代码块求值失败(沙箱拒绝或表达式错误): " + e.getMessage());
        }
    }
}
