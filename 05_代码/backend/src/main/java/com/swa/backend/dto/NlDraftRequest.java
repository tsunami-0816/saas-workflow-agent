package com.swa.backend.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/** NL→流程请求。 */
public record NlDraftRequest(
        @NotBlank @Size(max = 2000) String text,
        @Size(max = 128) String workflowName) {
}
