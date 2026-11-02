package com.example.CRM.otp;

import jakarta.persistence.*;
import lombok.*;

import java.time.LocalDateTime;


@Entity
@Table(name = "otp_codes")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class OtpCodeEntity {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 20)
    private String phone;

    @Column(nullable = false, length = 30)
    private String purpose; // SIGNUP, LOGIN

    @Column(name = "code_hash", nullable = false, length = 255)
    private String codeHash;

    @Column(name = "expires_at", nullable = false)
    private LocalDateTime expiresAt;

    @Column(name = "attempts_left", nullable = false)
    private int attemptsLeft;

    @Column(nullable = false)
    private boolean used;

    @Column(name = "created_at")
    private LocalDateTime createdAt;
}

