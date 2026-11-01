package com.swa.backend.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.swa.backend.common.BizException;
import com.swa.backend.common.ErrorCode;
import com.swa.backend.connector.CredentialCryptoService;
import com.swa.backend.dto.CredentialRequest;
import com.swa.backend.entity.ConnectorCredential;
import com.swa.backend.mapper.ConnectorCredentialMapper;
import org.springframework.stereotype.Service;

/**
 * 连接器凭据管理（BE-7.2，仅 admin）。
 * configJson 整体 AES 加密入库；对外返回一律脱敏（configJson 替换为 ******），密文不出库。
 */
@Service
public class CredentialService {

    /** 脱敏占位符。 */
    public static final String MASKED = "******";

    private final ConnectorCredentialMapper credentialMapper;
    private final CredentialCryptoService cryptoService;

    public CredentialService(ConnectorCredentialMapper credentialMapper, CredentialCryptoService cryptoService) {
        this.credentialMapper = credentialMapper;
        this.cryptoService = cryptoService;
    }

    public Page<ConnectorCredential> page(int pageNo, int pageSize) {
        Page<ConnectorCredential> page = credentialMapper.selectPage(new Page<>(pageNo, pageSize),
                new QueryWrapper<ConnectorCredential>().orderByDesc("id"));
        page.getRecords().forEach(c -> c.setConfigJson(MASKED));
        return page;
    }

    public ConnectorCredential get(Long id) {
        ConnectorCredential credential = credentialMapper.selectById(id);
        if (credential == null) {
            throw new BizException(ErrorCode.CREDENTIAL_NOT_FOUND);
        }
        credential.setConfigJson(MASKED);
        return credential;
    }

    /**
     * 创建凭据：configJson 整体加密后入库。
     */
    public ConnectorCredential create(CredentialRequest request) {
        ConnectorCredential credential = new ConnectorCredential();
        credential.setConnectorType(request.connectorType());
        credential.setName(request.name());
        credential.setConfigJson(cryptoService.encrypt(request.configJson()));
        credentialMapper.insert(credential);
        credential.setConfigJson(MASKED);
        return credential;
    }

    public ConnectorCredential update(Long id, CredentialRequest request) {
        ConnectorCredential credential = credentialMapper.selectById(id);
        if (credential == null) {
            throw new BizException(ErrorCode.CREDENTIAL_NOT_FOUND);
        }
        credential.setConnectorType(request.connectorType());
        credential.setName(request.name());
        credential.setConfigJson(cryptoService.encrypt(request.configJson()));
        credentialMapper.updateById(credential);
        credential.setConfigJson(MASKED);
        return credential;
    }

    public void delete(Long id) {
        if (credentialMapper.selectById(id) == null) {
            throw new BizException(ErrorCode.CREDENTIAL_NOT_FOUND);
        }
        credentialMapper.deleteById(id);
    }
}
