package com.example.CRM.otp.repository;

import com.example.CRM.otp.OtpCodeEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface OtpCodeRepository extends JpaRepository<OtpCodeEntity, Long> {
    Optional<OtpCodeEntity> findTopByPhoneAndPurposeOrderByIdDesc(String phone, String purpose);
}

