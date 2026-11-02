package com.example.CRM.settings.controller;

import com.example.CRM.settings.dto.SettingsResponse;
import com.example.CRM.settings.dto.SettingsUpdateRequest;
import com.example.CRM.settings.service.SettingsService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/settings")
@RequiredArgsConstructor
public class SettingsController {

    private final SettingsService service;

    @GetMapping
    public SettingsResponse get() {
        return service.getSettings();
    }

    @PutMapping
    public SettingsResponse update(@RequestBody SettingsUpdateRequest req) {
        return service.update(req);
    }
}
