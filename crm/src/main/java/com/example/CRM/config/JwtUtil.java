package com.example.CRM.config;

import io.jsonwebtoken.*;
import io.jsonwebtoken.security.Keys;
import org.springframework.stereotype.Component;

import javax.crypto.SecretKey;
import java.util.Date;
import java.util.Map;

@Component
public class JwtUtil {

    // ❗ kamida 256 bit bo‘lishi shart
    private static final String SECRET =
            "super-secret-key-for-crm-project-256-bit-minimum";

    private final SecretKey key = Keys.hmacShaKeyFor(SECRET.getBytes());

    private final long ACCESS_TOKEN_EXP = 1000 * 60 * 15; // 15 min

    // ================= CREATE =================
    public String generateToken(String username, String role) {
        return Jwts.builder()
                .subject(username)
                .claim("role", role)
                .issuedAt(new Date())
                .expiration(new Date(System.currentTimeMillis() + ACCESS_TOKEN_EXP))
                .signWith(key)
                .compact();
    }

    // ================= PARSE =================
    public Jws<Claims> parse(String token) {
        return Jwts.parser()
                .verifyWith(key)
                .build()
                .parseSignedClaims(token);
    }

    // ================= VALIDATE =================
    public boolean isValid(String token) {
        try {
            parse(token);
            return true;
        } catch (JwtException e) {
            return false;
        }
    }

    // ================= READ =================
    public String getUsername(String token) {
        return parse(token).getPayload().getSubject();
    }

    public String getRole(String token) {
        return parse(token).getPayload().get("role", String.class);
    }
}