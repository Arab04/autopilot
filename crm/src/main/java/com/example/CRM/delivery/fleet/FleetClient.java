package com.example.CRM.delivery.fleet;

import com.example.CRM.delivery.entity.DeliveryEntity;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientResponseException;

import java.util.HashMap;
import java.util.Map;

/**
 * Skuter flotining dispetcher API si (Arab04/autopilot, sim/world/flot.py). Kirish "X-API-Kalit" bilan
 * (serverda FLOT_API_KALIT).
 */
@Component
public class FleetClient {

    private final RestClient http;
    private final ObjectMapper json = new ObjectMapper();

    public FleetClient(RestClient.Builder builder,
                       @Value("${fleet.url}") String url,
                       @Value("${fleet.api-key}") String apiKey) {
        this.http = builder.baseUrl(url).defaultHeader("X-API-Kalit", apiKey).build();
    }

    public FleetOrder create(DeliveryEntity d) {
        Map<String, Object> body = new HashMap<>();
        body.put("lat", d.getLat());
        body.put("lon", d.getLon());
        body.put("nomi", d.getAddress());
        body.put("mijoz", d.getCustomerName());
        body.put("tel", d.getCustomerPhone());
        body.put("izoh", d.getNote() == null ? "" : d.getNote());
        byte[] bytes;
        try {
            bytes = json.writeValueAsBytes(body);
        } catch (com.fasterxml.jackson.core.JsonProcessingException e) {
            throw new FleetException("Buyurtmani JSON ga aylantirib bo'lmadi: " + e.getMessage());
        }
        // Content-Length aniq bo'lsin: flot serveri (Python http.server) "chunked" tanani o'qimaydi
        return call(() -> http.post().uri("/api/buyurtma").contentType(MediaType.APPLICATION_JSON)
                .contentLength(bytes.length).body(bytes).retrieve().body(FleetOrder.class));
    }

    public FleetOrder get(long fleetOrderId) {
        return call(() -> http.get().uri("/api/buyurtma/{id}", fleetOrderId).retrieve().body(FleetOrder.class));
    }

    private FleetOrder call(java.util.function.Supplier<FleetOrder> f) {
        try {
            FleetOrder o = f.get();
            if (o == null) throw new FleetException("Flot bo'sh javob qaytardi");
            return o;
        } catch (RestClientResponseException e) {
            throw new FleetException(errorText(e));
        } catch (ResourceAccessException e) {
            throw new FleetException("Flot serveriga ulanib bo'lmadi: " + e.getMessage());
        }
    }

    private String errorText(RestClientResponseException e) {
        try {
            JsonNode n = json.readTree(e.getResponseBodyAsString());
            if (n.hasNonNull("xato")) return n.get("xato").asText();
        } catch (Exception ignored) {
            // javob JSON emas
        }
        return "Flot xatosi: HTTP " + e.getStatusCode().value();
    }
}
