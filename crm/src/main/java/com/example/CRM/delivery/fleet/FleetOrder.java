package com.example.CRM.delivery.fleet;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

/** Flot API javobi (POST/GET /api/buyurtma). pin va kuzatish_havola (mijoz Telegram botiga havola) faqat yaratishda keladi. */
@JsonIgnoreProperties(ignoreUnknown = true)
public record FleetOrder(
        long id,
        String holat,
        String pin,
        Integer skuter,
        @JsonProperty("eta_daq") Double etaMinutes,
        @JsonProperty("kuzatish_havola") String trackingLink
) {
    public FleetOrder(long id, String holat, String pin, Integer skuter, Double etaMinutes) {
        this(id, holat, pin, skuter, etaMinutes, null);
    }
}
