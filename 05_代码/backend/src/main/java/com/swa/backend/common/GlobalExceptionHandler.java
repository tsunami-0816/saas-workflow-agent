package com.swa.backend.common;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.validation.BindException;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.MissingServletRequestParameterException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

/**
 * 全局异常处理：业务异常按错误码分段返回；参数校验异常归 10000；
 * 未知异常归 10500，日志记录完整堆栈（不打印任何密钥）。
 * HTTP 状态映射：10401→401、10403→403、40429→429，其余 200（code 承载业务语义）。
 */
@RestControllerAdvice
public class GlobalExceptionHandler {

    private static final Logger log = LoggerFactory.getLogger(GlobalExceptionHandler.class);

    @ExceptionHandler(BizException.class)
    public ResponseEntity<Result<Void>> handleBiz(BizException e) {
        log.warn("biz exception code={} msg={}", e.getCode(), e.getMessage());
        return ResponseEntity.status(httpStatusOf(e.getCode()))
                .body(Result.error(e.getCode(), e.getMessage()));
    }

    private static int httpStatusOf(int code) {
        return switch (code) {
            case 10401 -> 401;
            case 10403 -> 403;
            case 40429 -> 429;
            default -> 200;
        };
    }

    @ExceptionHandler({MethodArgumentNotValidException.class, BindException.class})
    public Result<Void> handleValidation(BindException e) {
        FieldError fe = e.getBindingResult().getFieldError();
        String detail = fe == null ? "参数校验失败" : fe.getField() + " " + fe.getDefaultMessage();
        return Result.error(ErrorCode.PARAM_ERROR, detail);
    }

    @ExceptionHandler({MissingServletRequestParameterException.class, HttpMessageNotReadableException.class})
    public Result<Void> handleBadRequest(Exception e) {
        return Result.error(ErrorCode.PARAM_ERROR, e.getMessage());
    }

    @ExceptionHandler(Exception.class)
    public Result<Void> handleUnknown(Exception e) {
        log.error("unhandled exception", e);
        return Result.error(ErrorCode.INTERNAL_ERROR);
    }
}
