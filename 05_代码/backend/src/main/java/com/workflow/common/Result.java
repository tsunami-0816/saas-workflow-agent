package com.workflow.common;
import lombok.Data;
@Data
public class Result<T> {
    private int code;
    private String message;
    private T data;
    public static <T> Result<T> ok(T data) { Result<T> r = new Result<>(); r.setCode(0); r.setMessage("ok"); r.setData(data); return r; }
}
