package com.example.CRM.delivery.service;

import lombok.RequiredArgsConstructor;
import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.annotation.EnableScheduling;
import org.springframework.scheduling.annotation.Scheduled;

/** Faol yetkazishlar holatini flotdan muntazam oladi (har fleet.sync-seconds soniyada). */
@Configuration
@EnableScheduling
@RequiredArgsConstructor
public class DeliverySync {

    private final DeliveryService service;

    @Scheduled(fixedDelayString = "${fleet.sync-seconds:30}", timeUnit = java.util.concurrent.TimeUnit.SECONDS,
            initialDelayString = "${fleet.sync-seconds:30}")
    public void sync() {
        service.syncActive();
    }
}
