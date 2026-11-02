package com.example.CRM.settings.service;


import com.example.CRM.settings.dto.SettingsResponse;
import com.example.CRM.settings.dto.SettingsUpdateRequest;
import com.example.CRM.settings.entity.SettingsEntity;
import com.example.CRM.settings.repository.SettingsRepository;
import jakarta.persistence.EntityNotFoundException;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

@Service
@RequiredArgsConstructor
public class SettingsServiceImpl implements SettingsService {

    private final SettingsRepository repo;

    private SettingsEntity getRow() {
        return repo.findById(1L).orElseThrow(() -> new EntityNotFoundException("Settings row not found"));
    }

    @Override
    public SettingsResponse getSettings() {
        return toResponse(getRow());
    }

    @Override
    public SettingsResponse update(SettingsUpdateRequest req) {
        SettingsEntity s = getRow();

        if (req.companyName() != null) s.setCompanyName(req.companyName());
        if (req.address() != null) s.setAddress(req.address());
        if (req.phone() != null) s.setPhone(req.phone());
        if (req.inn() != null) s.setInn(req.inn());

        if (req.baseCurrency() != null) s.setBaseCurrency(req.baseCurrency());
        if (req.usdRate() != null) s.setUsdRate(req.usdRate());
        if (req.autoRate() != null) s.setAutoRate(req.autoRate());

        if (req.taxPercent() != null) s.setTaxPercent(req.taxPercent());

        if (req.smsEnabled() != null) s.setSmsEnabled(req.smsEnabled());
        if (req.telegramEnabled() != null) s.setTelegramEnabled(req.telegramEnabled());
        if (req.remindDaysBefore() != null) s.setRemindDaysBefore(req.remindDaysBefore());
        if (req.remindTemplate() != null) s.setRemindTemplate(req.remindTemplate());
        if (req.overdueTemplate() != null) s.setOverdueTemplate(req.overdueTemplate());

        repo.save(s);
        return toResponse(s);
    }

    private SettingsResponse toResponse(SettingsEntity s) {
        return new SettingsResponse(
                s.getCompanyName(), s.getAddress(), s.getPhone(), s.getInn(),
                s.getBaseCurrency(), s.getUsdRate(), s.isAutoRate(),
                s.getTaxPercent(),
                s.isSmsEnabled(), s.isTelegramEnabled(),
                s.getRemindDaysBefore(), s.getRemindTemplate(), s.getOverdueTemplate()
        );
    }
}
