package com.swa.backend.connector;

import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Map;

/**
 * OCR Mock 连接器（BE-7.5 增强项）。
 * ⚠️ 协议替身，非真实 OCR 厂商：不发起任何外部调用，仅按真实 OCR 接口的响应结构返回模拟数据，
 * 供链路/计量联调使用。接入真实 OCR 时按 Connector SPI 新增实现类即可，不动引擎。
 *
 * 输入：config.text（待识别文本，模拟图片内容）；
 * 输出：{text, confidence, words:[...], mock:true}。
 */
@Component
public class OcrMockConnector implements Connector {

    @Override
    public String type() {
        return "ocr-mock";
    }

    @Override
    public Map<String, Object> execute(Map<String, Object> config, Map<String, Object> input) {
        String text = config != null && config.get("text") != null
                ? String.valueOf(config.get("text"))
                : String.valueOf(input == null ? "" : input.getOrDefault("_payload", ""));
        return Map.of(
                "text", text,
                "confidence", 0.99,
                "words", List.of(Map.of("word", text, "confidence", 0.99)),
                "mock", true);
    }
}
