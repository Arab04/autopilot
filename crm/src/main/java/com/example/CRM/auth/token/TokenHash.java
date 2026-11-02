package com.example.CRM.auth.token;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.util.Base64;

public final class TokenHash {
    private TokenHash(){}

    public static String sha256(String raw) {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            byte[] out = md.digest(raw.getBytes(StandardCharsets.UTF_8));
            return Base64.getEncoder().encodeToString(out);
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }

    public static String randomToken() {
        byte[] b = new byte[48];
        new SecureRandom().nextBytes(b);
        return Base64.getUrlEncoder().withoutPadding().encodeToString(b);
    }

    public static String randomOtp6() {
        int x = 100000 + new SecureRandom().nextInt(900000);
        return String.valueOf(x);
    }
}

