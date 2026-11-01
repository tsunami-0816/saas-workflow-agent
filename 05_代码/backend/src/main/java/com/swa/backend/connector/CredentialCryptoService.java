package com.swa.backend.connector;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import javax.crypto.Cipher;
import javax.crypto.spec.IvParameterSpec;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.security.SecureRandom;
import java.util.Base64;

/**
 * 凭据 AES 加解密（BE-7.2）：AES/CBC/PKCS5Padding，密钥走环境变量 CREDENTIAL_AES_KEY
 * （32 字节 utf8 或 64 位 hex）。密文输出格式 base64(iv) + ":" + base64(cipher)。
 * 禁止在日志中打印明文与密钥。
 */
@Component
public class CredentialCryptoService {

    private static final SecureRandom RANDOM = new SecureRandom();
    private final SecretKeySpec keySpec;

    public CredentialCryptoService(@Value("${security.credential-aes-key}") String key) {
        byte[] raw;
        if (key.matches("[0-9a-fA-F]{64}")) {
            raw = hexToBytes(key);
        } else {
            raw = key.getBytes(StandardCharsets.UTF_8);
        }
        if (raw.length != 16 && raw.length != 24 && raw.length != 32) {
            throw new IllegalStateException("CREDENTIAL_AES_KEY 长度须为 16/24/32 字节或 64 位 hex");
        }
        // 统一取前 16 字节做 AES-128（24/32 亦可直接用）
        this.keySpec = new SecretKeySpec(raw.length == 16 ? raw : java.util.Arrays.copyOf(raw, raw.length == 24 ? 24 : 32), "AES");
    }

    /**
     * 加密明文。
     */
    public String encrypt(String plain) {
        try {
            byte[] iv = new byte[16];
            RANDOM.nextBytes(iv);
            Cipher cipher = Cipher.getInstance("AES/CBC/PKCS5Padding");
            cipher.init(Cipher.ENCRYPT_MODE, keySpec, new IvParameterSpec(iv));
            byte[] encrypted = cipher.doFinal(plain.getBytes(StandardCharsets.UTF_8));
            return Base64.getEncoder().encodeToString(iv) + ":" + Base64.getEncoder().encodeToString(encrypted);
        } catch (Exception e) {
            throw new IllegalStateException("凭据加密失败");
        }
    }

    /**
     * 解密密文。
     */
    public String decrypt(String cipherText) {
        try {
            String[] parts = cipherText.split(":", 2);
            Cipher cipher = Cipher.getInstance("AES/CBC/PKCS5Padding");
            cipher.init(Cipher.DECRYPT_MODE, keySpec,
                    new IvParameterSpec(Base64.getDecoder().decode(parts[0])));
            return new String(cipher.doFinal(Base64.getDecoder().decode(parts[1])), StandardCharsets.UTF_8);
        } catch (Exception e) {
            throw new IllegalStateException("凭据解密失败");
        }
    }

    private static byte[] hexToBytes(String hex) {
        byte[] out = new byte[hex.length() / 2];
        for (int i = 0; i < out.length; i++) {
            out[i] = (byte) Integer.parseInt(hex.substring(i * 2, i * 2 + 2), 16);
        }
        return out;
    }
}
