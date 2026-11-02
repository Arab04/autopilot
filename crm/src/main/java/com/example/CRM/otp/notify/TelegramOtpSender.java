package com.example.CRM.otp.notify;

import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.util.Map;

@Service
@RequiredArgsConstructor
public class TelegramOtpSender {

    @Value("${telegram.bot.token}")
    private String botToken;

    @Value("${telegram.bot.channel-id}")
    private String chatId;

    private final RestTemplate restTemplate = new RestTemplate();

    public void sendOtp(String phone, String otp, String purpose) {
        String text = "OTP (" + purpose + ")\nPhone: " + phone + "\nCode: " + otp;
        String url = "https://api.telegram.org/bot" + botToken + "/sendMessage";
        Map<String, Object> body = Map.of("chat_id", chatId, "text", text);
        restTemplate.postForObject(url, body, String.class);
    }
}
