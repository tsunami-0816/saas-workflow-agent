package com.swa.backend.config;

import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Info;
import io.swagger.v3.oas.models.security.SecurityRequirement;
import io.swagger.v3.oas.models.security.SecurityScheme;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * springdoc OpenAPI：输出 /v3/api-docs，供第 6.5 步契约校验。
 */
@Configuration
public class OpenApiConfig {

    @Bean
    public OpenAPI swaOpenAPI() {
        final String bearer = "bearerAuth";
        return new OpenAPI()
                .info(new Info().title("saas-workflow-agent API").version("v1")
                        .description("SaaS 自动化工作流编排平台 java-backend 契约"))
                .schemaRequirement(bearer, new SecurityScheme()
                        .type(SecurityScheme.Type.HTTP).scheme("bearer").bearerFormat("JWT"))
                .addSecurityItem(new SecurityRequirement().addList(bearer));
    }
}
