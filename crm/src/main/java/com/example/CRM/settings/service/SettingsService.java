package com.example.CRM.settings.service;

import com.example.CRM.settings.dto.SettingsResponse;
import com.example.CRM.settings.dto.SettingsUpdateRequest;

public interface SettingsService {
    SettingsResponse getSettings();
    SettingsResponse update(SettingsUpdateRequest req);
}