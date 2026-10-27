package com.workflow.repo;
import com.workflow.entity.WorkflowRun;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;
public interface WorkflowRunRepository extends JpaRepository<WorkflowRun, Long> {
    List<WorkflowRun> findByWorkflowIdOrderByIdDesc(Long workflowId);
}
