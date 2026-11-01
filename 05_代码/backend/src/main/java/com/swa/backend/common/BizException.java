package com.swa.backend.common;

/**
 * 业务异常：携带错误码，由 GlobalExceptionHandler 统一转为响应壳。
 */
public class BizException extends RuntimeException {

    private final int code;

    public BizException(ErrorCode errorCode) {
        super(errorCode.getMessage());
        this.code = errorCode.getCode();
    }

    public BizException(ErrorCode errorCode, String detail) {
        super(errorCode.getMessage() + ": " + detail);
        this.code = errorCode.getCode();
    }

    public int getCode() {
        return code;
    }
}
