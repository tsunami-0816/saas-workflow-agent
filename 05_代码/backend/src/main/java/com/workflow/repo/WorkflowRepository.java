package com.workflow.repo;
import com.workflow.entity.Workflow;
import org.springframework.data.jpa.repository.JpaRepository;
public interface WorkflowRepository extends JpaRepository<Workflow, Long> {}
