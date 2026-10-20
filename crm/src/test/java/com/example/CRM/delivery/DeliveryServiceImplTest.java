package com.example.CRM.delivery;

import com.example.CRM.delivery.dto.DeliveryRequest;
import com.example.CRM.delivery.entity.DeliveryEntity;
import com.example.CRM.delivery.entity.DeliveryStatus;
import com.example.CRM.delivery.fleet.FleetClient;
import com.example.CRM.delivery.fleet.FleetException;
import com.example.CRM.delivery.fleet.FleetOrder;
import com.example.CRM.delivery.repository.DeliveryRepository;
import com.example.CRM.delivery.service.DeliveryServiceImpl;
import com.example.CRM.sale.entity.SaleEntity;
import com.example.CRM.sale.repository.SaleRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

/** Ma'lumotlar bazasisiz: repository va flot mock. */
class DeliveryServiceImplTest {

    DeliveryRepository repo;
    SaleRepository sales;
    FleetClient fleet;
    DeliveryServiceImpl service;

    @BeforeEach
    void setUp() {
        repo = mock(DeliveryRepository.class);
        sales = mock(SaleRepository.class);
        fleet = mock(FleetClient.class);
        when(repo.save(any())).thenAnswer(a -> {
            DeliveryEntity d = a.getArgument(0);
            if (d.getId() == null) d.setId(1L);
            return d;
        });
        service = new DeliveryServiceImpl(repo, sales, fleet);
    }

    private static DeliveryRequest req(Long saleId, String name, String phone) {
        return new DeliveryRequest(saleId, name, phone, "Pedagogika universiteti", 41.4708, 69.5742, null);
    }

    @Test
    void createSendsToFleetAndStoresPin() {
        when(fleet.create(any())).thenReturn(new FleetOrder(7, "tayinlandi", "0420", 2, 13.5, "https://t.me/b?start=7_k"));
        DeliveryEntity d = service.create(req(null, "Ali", "+998901234567"));
        assertEquals("https://t.me/b?start=7_k", d.getTrackingLink());
        assertEquals(DeliveryStatus.ASSIGNED, d.getStatus());
        assertEquals(7L, d.getFleetOrderId());
        assertEquals("0420", d.getPin());
        assertEquals(2, d.getScooterId());
        assertEquals(13.5, d.getEtaMinutes());
        assertNull(d.getError());
    }

    @Test
    void fleetRejectionIsSavedAsFailedAndRetriedOnRefresh() {
        when(fleet.create(any())).thenThrow(new FleetException("manzil xizmat hududidan tashqarida"));
        DeliveryEntity d = service.create(req(null, "Ali", "+99890"));
        assertEquals(DeliveryStatus.FAILED, d.getStatus());
        assertEquals("manzil xizmat hududidan tashqarida", d.getError());

        reset(fleet);
        when(fleet.create(any())).thenReturn(new FleetOrder(8, "yangi", "1111", null, null));
        when(repo.findById(1L)).thenReturn(Optional.of(d));
        DeliveryEntity r = service.refresh(1L);
        assertEquals(DeliveryStatus.QUEUED, r.getStatus());
        assertEquals(8L, r.getFleetOrderId());
        assertNull(r.getError());
    }

    @Test
    void customerTakenFromSaleWhenMissing() {
        SaleEntity s = new SaleEntity();
        s.setCustomerName("Vali");
        s.setCustomerPhone("+998935554433");
        when(sales.findById(5L)).thenReturn(Optional.of(s));
        when(fleet.create(any())).thenReturn(new FleetOrder(9, "yangi", "2222", null, 30.0));
        DeliveryEntity d = service.create(req(5L, "", null));
        assertEquals("Vali", d.getCustomerName());
        assertEquals("+998935554433", d.getCustomerPhone());
        assertEquals(5L, d.getSaleId());
    }

    @Test
    void missingCustomerIsRejectedBeforeFleet() {
        assertThrows(IllegalArgumentException.class, () -> service.create(req(null, "Ali", " ")));
        verifyNoInteractions(fleet);
    }

    @Test
    void syncUpdatesActiveDeliveriesAndMarksDelivered() {
        DeliveryEntity a = DeliveryEntity.builder().id(1L).fleetOrderId(11L).status(DeliveryStatus.ON_THE_WAY).build();
        DeliveryEntity b = DeliveryEntity.builder().id(2L).fleetOrderId(12L).status(DeliveryStatus.ASSIGNED).build();
        when(repo.findByStatusIn(any())).thenReturn(List.of(a, b));
        when(fleet.get(11L)).thenReturn(new FleetOrder(11, "topshirildi", null, 3, null));
        when(fleet.get(12L)).thenThrow(new FleetException("Flot serveriga ulanib bo'lmadi"));
        assertEquals(1, service.syncActive());
        assertEquals(DeliveryStatus.DELIVERED, a.getStatus());
        assertNotNull(a.getDeliveredAt());
        assertNull(a.getEtaMinutes());
        assertEquals(DeliveryStatus.ASSIGNED, b.getStatus());   // ulanmasa holat o'zgarmaydi
    }

    @Test
    void fleetStatusMapping() {
        assertEquals(DeliveryStatus.ARRIVED, DeliveryStatus.fromFleet("yetib_keldi"));
        assertEquals(DeliveryStatus.RETURNED, DeliveryStatus.fromFleet("qaytarildi"));
        assertThrows(IllegalArgumentException.class, () -> DeliveryStatus.fromFleet("boshqa"));
    }
}
