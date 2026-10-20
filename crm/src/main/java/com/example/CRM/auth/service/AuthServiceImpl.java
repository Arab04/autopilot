package com.example.CRM.auth.service;

import com.example.CRM.auth.dto.AuthResponse;
import com.example.CRM.auth.entity.UserEntity;
import com.example.CRM.auth.repository.UserRepository;
import com.example.CRM.auth.token.TokenHash;
import com.example.CRM.config.JwtUtil;
import com.example.CRM.otp.OtpCodeEntity;
import com.example.CRM.otp.notify.TelegramOtpSender;
import com.example.CRM.otp.repository.OtpCodeRepository;
import com.example.CRM.refresh.RefreshTokenEntity;
import com.example.CRM.refresh.dto.TokenResponse;
import com.example.CRM.refresh.repository.RefreshTokenRepository;
import jakarta.persistence.EntityNotFoundException;
import jakarta.transaction.Transactional;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.Objects;

@Service
@RequiredArgsConstructor
public class AuthServiceImpl implements AuthService {

    private final UserRepository userRepo;
    private final OtpCodeRepository otpRepo;
    private final RefreshTokenRepository refreshRepo;

    private final BCryptPasswordEncoder encoder;
    private final JwtUtil jwtUtil;
    private final TelegramOtpSender telegram;

    @Value("${app.jwt.refreshMinutes}")
    private long refreshMinutes;

    private static final int OTP_ATTEMPTS = 5;
    private static final int OTP_TTL_MIN = 3;

    @Override
    @Transactional
    public void signupRequestOtp(String phone) {
        if (userRepo.existsByPhone(phone)) {
            throw new IllegalArgumentException("Bu telefon allaqachon ro‘yxatdan o‘tgan");
        }
        issueOtp(phone, "SIGNUP");
    }

    @Override
    @Transactional
    public TokenResponse signupConfirm(String phone, String otp, String password, String confirmPassword) {
        if (!Objects.equals(password, confirmPassword)) {
            throw new IllegalArgumentException("Password mos emas");
        }
        verifyOtp(phone, "SIGNUP", otp);

        UserEntity user = UserEntity.builder()
                .username(phone)              // username sifatida phone ishlatsak bo‘ladi
                .phone(phone)
                .password(encoder.encode(password))
                .role("CLIENT")
                .userType("CLIENT")
                .enabled(true)
                .build();

        userRepo.save(user);
        return issueTokens(user);
    }

    @Override
    @Transactional
    public void loginRequestOtp(String phone, String password) {
        UserEntity user = userRepo.findByPhone(phone)
                .orElseThrow(() -> new EntityNotFoundException("User topilmadi"));

        if (!user.isEnabled()) throw new IllegalArgumentException("User bloklangan");
        if (!encoder.matches(password, user.getPassword())) {
            throw new IllegalArgumentException("Telefon yoki parol noto‘g‘ri");
        }

        issueOtp(phone, "LOGIN");
    }

    @Override
    @Transactional
    public TokenResponse loginConfirm(String phone, String otp) {
        UserEntity user = userRepo.findByPhone(phone)
                .orElseThrow(() -> new EntityNotFoundException("User topilmadi"));

        verifyOtp(phone, "LOGIN", otp);
        return issueTokens(user);
    }

    @Override
    @Transactional
    public TokenResponse refresh(String refreshToken) {
        String hash = TokenHash.sha256(refreshToken);
        RefreshTokenEntity stored = refreshRepo.findByTokenHash(hash)
                .orElseThrow(() -> new IllegalArgumentException("Refresh token noto‘g‘ri"));

        if (stored.isRevoked()) throw new IllegalArgumentException("Refresh revoked");
        if (stored.getExpiresAt().isBefore(LocalDateTime.now())) throw new IllegalArgumentException("Refresh expired");

        UserEntity user = userRepo.findById(stored.getUserId())
                .orElseThrow(() -> new EntityNotFoundException("User topilmadi"));

        // rotation: eski refresh revoke, yangi beramiz
        stored.setRevoked(true);
        refreshRepo.save(stored);

        return issueTokens(user);
    }

    @Override
    @Transactional
    public void logout(String refreshToken) {
        String hash = TokenHash.sha256(refreshToken);
        refreshRepo.findByTokenHash(hash).ifPresent(t -> {
            t.setRevoked(true);
            refreshRepo.save(t);
        });
    }

    // ===== helpers =====

    private void issueOtp(String phone, String purpose) {
        String otp = TokenHash.randomOtp6();
        String otpHash = encoder.encode(otp);

        OtpCodeEntity entity = OtpCodeEntity.builder()
                .phone(phone)
                .purpose(purpose)
                .codeHash(otpHash)
                .expiresAt(LocalDateTime.now().plusMinutes(OTP_TTL_MIN))
                .attemptsLeft(OTP_ATTEMPTS)
                .used(false)
                .createdAt(LocalDateTime.now())
                .build();

        otpRepo.save(entity);
        telegram.sendOtp(phone, otp, purpose);
    }

    private void verifyOtp(String phone, String purpose, String otp) {
        OtpCodeEntity last = otpRepo.findTopByPhoneAndPurposeOrderByIdDesc(phone, purpose)
                .orElseThrow(() -> new IllegalArgumentException("OTP topilmadi"));

        if (last.isUsed()) throw new IllegalArgumentException("OTP ishlatilgan");
        if (last.getExpiresAt().isBefore(LocalDateTime.now())) throw new IllegalArgumentException("OTP eskirgan");
        if (last.getAttemptsLeft() <= 0) throw new IllegalArgumentException("OTP urinishlar tugagan");

        if (!encoder.matches(otp, last.getCodeHash())) {
            last.setAttemptsLeft(last.getAttemptsLeft() - 1);
            otpRepo.save(last);
            throw new IllegalArgumentException("OTP noto‘g‘ri");
        }

        last.setUsed(true);
        otpRepo.save(last);
    }

    private TokenResponse issueTokens(UserEntity user) {
        String access = jwtUtil.generateToken(user.getUsername(), user.getRole());

        String refreshRaw = TokenHash.randomToken();
        String refreshHash = TokenHash.sha256(refreshRaw);

        RefreshTokenEntity rt = RefreshTokenEntity.builder()
                .userId(user.getId())
                .tokenHash(refreshHash)
                .expiresAt(LocalDateTime.now().plusMinutes(refreshMinutes)) // 120 min
                .revoked(false)
                .createdAt(LocalDateTime.now())
                .build();

        refreshRepo.save(rt);

        return new TokenResponse(access, refreshRaw);
    }
}