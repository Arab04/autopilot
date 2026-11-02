package com.example.CRM.credit.repository;

import com.example.CRM.credit.entity.CreditEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface CreditRepository extends JpaRepository<CreditEntity, Long> {}
