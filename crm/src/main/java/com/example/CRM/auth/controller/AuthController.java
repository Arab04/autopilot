package com.example.CRM.auth.controller;

import com.example.CRM.auth.service.AuthService;
import com.example.CRM.otp.dto.LoginConfirm;
import com.example.CRM.otp.dto.LoginRequestOtp;
import com.example.CRM.otp.dto.SignupConfirm;
import com.example.CRM.otp.dto.SignupRequestOtp;
import com.example.CRM.refresh.dto.LogoutRequest;
import com.example.CRM.refresh.dto.RefreshRequest;
import com.example.CRM.refresh.dto.TokenResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/auth")
@RequiredArgsConstructor
public class AuthController {

    private final AuthService authService;

    @PostMapping("/signup/request-otp")
    public void signupRequestOtp(@RequestBody SignupRequestOtp req) {
        authService.signupRequestOtp(req.phone());
    }

    @PostMapping("/signup/confirm")
    public TokenResponse signupConfirm(@RequestBody SignupConfirm req) {
        return authService.signupConfirm(req.phone(), req.otp(), req.password(), req.confirmPassword());
    }

    @PostMapping("/login/request-otp")
    public void loginRequestOtp(@RequestBody LoginRequestOtp req) {
        authService.loginRequestOtp(req.phone(), req.password());
    }

    @PostMapping("/login/confirm")
    public TokenResponse loginConfirm(@RequestBody LoginConfirm req) {
        return authService.loginConfirm(req.phone(), req.otp());
    }

    @PostMapping("/refresh")
    public TokenResponse refresh(@RequestBody RefreshRequest req) {
        return authService.refresh(req.refreshToken());
    }

    @PostMapping("/logout")
    public void logout(@RequestBody LogoutRequest req) {
        authService.logout(req.refreshToken());
    }
}