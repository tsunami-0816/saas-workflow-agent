package com.workflow.entity;
import jakarta.persistence.*;
import lombok.Data;
@Data
@Entity
@Table(name = "workflows")
public class Workflow {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    private Long tenantId;
    private String name;
    @Column(columnDefinition = "TEXT")
    private String definitionJson;
    private Integer status;
}
