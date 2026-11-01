package com.workflow.controller;
import com.workflow.common.Result;
import com.workflow.entity.Workflow;
import com.workflow.entity.WorkflowRun;
import com.workflow.repo.WorkflowRepository;
import com.workflow.repo.WorkflowRunRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;
import java.util.List;

@RestController
@RequestMapping("/api/workflows")
@RequiredArgsConstructor
public class WorkflowController {
    private final WorkflowRepository workflowRepo;
    private final WorkflowRunRepository runRepo;

    @GetMapping
    public Result<List<Workflow>> list() { return Result.ok(workflowRepo.findAll()); }

    @PostMapping
    public Result<Workflow> save(@RequestBody Workflow w) { return Result.ok(workflowRepo.save(w)); }

    @PostMapping("/{id}/run")
    public Result<WorkflowRun> run(@PathVariable Long id) {
        WorkflowRun run = new WorkflowRun();
        run.setWorkflowId(id);
        run.setStatus("RUNNING");
        run.setCurrentNode("start");
        run.setStartedAt(System.currentTimeMillis());
        run = runRepo.save(run);
        // Mock DAG执行：顺序走3个节点
        try { Thread.sleep(500); } catch(Exception e) {}
        run.setCurrentNode("http_call");
        runRepo.save(run);
        try { Thread.sleep(500); } catch(Exception e) {}
        run.setCurrentNode("agent_task");
        runRepo.save(run);
        try { Thread.sleep(500); } catch(Exception e) {}
        run.setStatus("SUCCESS");
        run.setResult("流程执行完成：start→http_call→agent_task→end");
        run.setFinishedAt(System.currentTimeMillis());
        return Result.ok(runRepo.save(run));
    }

    @GetMapping("/{id}/runs")
    public Result<List<WorkflowRun>> runs(@PathVariable Long id) {
        return Result.ok(runRepo.findByWorkflowIdOrderByIdDesc(id));
    }
}
