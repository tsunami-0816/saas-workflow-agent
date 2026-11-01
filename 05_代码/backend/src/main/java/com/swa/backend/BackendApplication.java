package com.swa.backend;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableAsync;

/**
 * saas-workflow-agent java-backend 启动类。
 * 单模块多包内聚：common/config/security/entity/mapper/service/controller/engine/llm/connector/mqtt/nl。
 */
@EnableAsync
@SpringBootApplication
@MapperScan("com.swa.backend.mapper")
public class BackendApplication {

    public static void main(String[] args) {
        SpringApplication.run(BackendApplication.class, args);
    }
}
