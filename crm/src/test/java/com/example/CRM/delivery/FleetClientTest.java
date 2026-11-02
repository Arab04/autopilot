package com.example.CRM.delivery;

import com.example.CRM.delivery.entity.DeliveryEntity;
import com.example.CRM.delivery.fleet.FleetClient;
import com.example.CRM.delivery.fleet.FleetException;
import com.example.CRM.delivery.fleet.FleetOrder;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestClient;

import static org.junit.jupiter.api.Assertions.*;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.*;
import static org.springframework.test.web.client.response.MockRestResponseCreators.*;

/** Flot API bilan HTTP shartnomasi: yo'l, kalit sarlavhasi, JSON maydonlari, xato matni. */
class FleetClientTest {

    @Test
    void createPostsOrderWithApiKeyAndParsesReply() {
        RestClient.Builder b = RestClient.builder();
        MockRestServiceServer server = MockRestServiceServer.bindTo(b).build();
        FleetClient client = new FleetClient(b, "https://flot.test", "kalit-123");
        server.expect(requestTo("https://flot.test/api/buyurtma"))
                .andExpect(method(HttpMethod.POST))
                .andExpect(header("X-API-Kalit", "kalit-123"))
                .andExpect(jsonPath("$.lat").value(41.4708))
                .andExpect(jsonPath("$.nomi").value("Pedagogika universiteti"))
                .andExpect(jsonPath("$.tel").value("+99890"))
                .andRespond(withStatus(HttpStatus.CREATED).contentType(MediaType.APPLICATION_JSON).body(
                        "{\"id\": 4, \"holat\": \"tayinlandi\", \"pin\": \"0815\", \"skuter\": 1, \"eta_daq\": 12.3, \"manba\": \"crm\", \"kuzatish_havola\": \"https://t.me/b?start=4_x\"}"));
        FleetOrder o = client.create(DeliveryEntity.builder().lat(41.4708).lon(69.5742)
                .address("Pedagogika universiteti").customerName("Ali").customerPhone("+99890").build());
        assertEquals(4, o.id());
        assertEquals("0815", o.pin());
        assertEquals("https://t.me/b?start=4_x", o.trackingLink());
        assertEquals(12.3, o.etaMinutes());
        server.verify();
    }

    @Test
    void fleetErrorTextIsPassedThrough() {
        RestClient.Builder b = RestClient.builder();
        MockRestServiceServer server = MockRestServiceServer.bindTo(b).build();
        FleetClient client = new FleetClient(b, "https://flot.test", "k");
        server.expect(requestTo("https://flot.test/api/buyurtma/9"))
                .andRespond(withStatus(HttpStatus.NOT_FOUND).contentType(MediaType.APPLICATION_JSON)
                        .body("{\"xato\": \"buyurtma topilmadi\"}"));
        FleetException e = assertThrows(FleetException.class, () -> client.get(9));
        assertEquals("buyurtma topilmadi", e.getMessage());
    }
}
