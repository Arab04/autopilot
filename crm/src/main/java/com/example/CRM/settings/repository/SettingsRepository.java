package com.example.CRM.settings.repository;

import com.example.CRM.settings.entity.SettingsEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface SettingsRepository extends JpaRepository<SettingsEntity, Long> {}