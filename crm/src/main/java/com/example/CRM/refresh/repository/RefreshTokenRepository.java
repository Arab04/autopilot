package com.example.CRM.refresh.repository;

import com.example.CRM.refresh.RefreshTokenEntity;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface RefreshTokenRepository extends JpaRepository<RefreshTokenEntity, Long> {
    Optional<RefreshTokenEntity> findByTokenHash(String tokenHash);
    List<RefreshTokenEntity> findAllByUserIdAndRevokedFalse(Long userId);
}