package com.workflow.entity;
import jakarta.persistence.*;
import lombok.Data;
@Data
@Entity
@Table(name = "workflow_runs")
public class WorkflowRun {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    private Long workflowId;
    private String status;
    private String currentNode;
    @Column(columnDefinition = "TEXT")
    private String result;
    private Long startedAt;
    private Long finishedAt;
}
