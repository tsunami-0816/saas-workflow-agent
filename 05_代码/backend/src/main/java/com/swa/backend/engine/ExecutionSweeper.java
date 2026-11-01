package com.swa.backend.engine;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.swa.backend.common.TenantContext;
import com.swa.backend.entity.Execution;
import com.swa.backend.entity.NodeExecution;
import com.swa.backend.mapper.ExecutionMapper;
import com.swa.backend.mapper.NodeExecutionMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.util.List;

/**
 * 悬挂执行收敛（BE-4.10）：应用启动时将 RUNNING/WAITING 的 execution 收敛为
 * FAILED(fail_reason=engine_restart)，其 RUNNING/WAITING/PENDING 节点一并 FAILED，
 * 保证 kill 重启后无悬挂实例。WAITING 节点虽由 DLX 消息可恢复，但重启场景口径统一收敛。
 */
@Component
public class ExecutionSweeper implements ApplicationRunner {

    private static final Logger log = LoggerFactory.getLogger(ExecutionSweeper.class);

    private final ExecutionMapper executionMapper;
    private final NodeExecutionMapper nodeExecutionMapper;

    public ExecutionSweeper(ExecutionMapper executionMapper, NodeExecutionMapper nodeExecutionMapper) {
        this.executionMapper = executionMapper;
        this.nodeExecutionMapper = nodeExecutionMapper;
    }

    @Override
    public void run(ApplicationArguments args) {
        List<Execution> hanging = executionMapper.selectByStatusIgnoreTenant(List.of("RUNNING", "WAITING"));
        if (hanging.isEmpty()) {
            log.info("sweeper: no hanging execution");
            return;
        }
        int converged = 0;
        for (Execution execution : hanging) {
            TenantContext.setTenantId(execution.getTenantId());
            try {
                execution.setStatus("FAILED");
                execution.setFailReason("engine_restart");
                execution.setEndedAt(LocalDateTime.now());
                executionMapper.updateById(execution);

                List<NodeExecution> activeNodes = nodeExecutionMapper.selectList(
                        new QueryWrapper<NodeExecution>().eq("execution_id", execution.getId())
                                .in("status", "RUNNING", "WAITING", "PENDING"));
                for (NodeExecution node : activeNodes) {
                    node.setStatus("FAILED");
                    node.setErrorMessage("engine_restart");
                    node.setEndedAt(LocalDateTime.now());
                    nodeExecutionMapper.updateById(node);
                }
                converged++;
            } finally {
                TenantContext.clear();
            }
        }
        log.info("sweeper: converged {} hanging executions (reason=engine_restart)", converged);
    }
}
