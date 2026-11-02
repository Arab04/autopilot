package com.example.CRM.unit.service;

import com.example.CRM.unit.entity.UnitEntity;
import com.example.CRM.unit.dto.UnitCreateRequest;
import com.example.CRM.unit.repository.UnitRepository;
import jakarta.persistence.EntityNotFoundException;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
@RequiredArgsConstructor
public class UnitServiceImpl implements UnitService {

    private final UnitRepository repo;

    @Override
    public UnitEntity create(UnitCreateRequest req) {
        // category ichida faqat 1 ta main bo‘lsin:
        if (req.mainUnit()) {
            repo.findAllByCategory(req.category()).forEach(u -> {
                if (u.isMainUnit()) { u.setMainUnit(false); repo.save(u); }
            });
        }

        UnitEntity u = UnitEntity.builder()
                .name(req.name())
                .symbol(req.symbol())
                .category(req.category())
                .mainUnit(req.mainUnit())
                .coefficient(req.coefficient())
                .build();

        return repo.save(u);
    }

    @Override
    public List<UnitEntity> list(String category) {
        if (category == null || category.isBlank()) return repo.findAll();
        return repo.findAllByCategory(category);
    }

    @Override
    public UnitEntity update(Long id, UnitCreateRequest req) {
        UnitEntity u = repo.findById(id).orElseThrow(() -> new EntityNotFoundException("Unit not found"));

        u.setName(req.name());
        u.setSymbol(req.symbol());
        u.setCategory(req.category());
        u.setCoefficient(req.coefficient());

        if (req.mainUnit()) {
            repo.findAllByCategory(req.category()).forEach(x -> {
                if (x.isMainUnit() && !x.getId().equals(id)) { x.setMainUnit(false); repo.save(x); }
            });
        }
        u.setMainUnit(req.mainUnit());

        return repo.save(u);
    }

    @Override
    public void delete(Long id) {
        repo.deleteById(id);
    }
}