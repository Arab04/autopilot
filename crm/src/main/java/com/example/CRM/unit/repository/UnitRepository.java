package com.example.CRM.unit.repository;

import com.example.CRM.unit.entity.UnitEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
@Repository
public interface UnitRepository extends JpaRepository<UnitEntity, Long> {
    List<UnitEntity> findAllByCategory(String category);
}