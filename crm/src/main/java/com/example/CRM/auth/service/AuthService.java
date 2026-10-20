package com.example.CRM.auth.service;

import com.example.CRM.refresh.dto.TokenResponse;

public interface AuthService {
    void signupRequestOtp(String phone);
    TokenResponse signupConfirm(String phone, String otp, String password, String confirmPassword);

    void loginRequestOtp(String phone, String password);
    TokenResponse loginConfirm(String phone, String otp);

    TokenResponse refresh(String refreshToken);
    void logout(String refreshToken);
}