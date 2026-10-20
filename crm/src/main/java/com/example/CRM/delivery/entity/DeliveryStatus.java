package com.example.CRM.delivery.entity;

/**
 * Yetkazish holati. Flot (skuter dispetcheri) holatlaridan moslanadi, qarang: {@link #fromFleet(String)}.
 */
public enum DeliveryStatus {
    NEW,          // CRM da yaratildi, flotga hali yuborilmadi
    FAILED,       // flot qabul qilmadi (xato matni error maydonida)
    QUEUED,       // flotda navbatda (bo'sh skuter kutmoqda)
    ASSIGNED,     // skuterga berildi, omborda yuklanmoqda
    ON_THE_WAY,   // skuter mijozga ketmoqda
    ARRIVED,      // skuter yetib keldi, mijoz PIN bilan qutini ochadi
    DELIVERED,    // topshirildi
    RETURNED,     // mijoz kelmadi, yuk omborga qaytdi
    CANCELLED;

    public boolean isActive() {
        return this == QUEUED || this == ASSIGNED || this == ON_THE_WAY || this == ARRIVED;
    }

    public static DeliveryStatus fromFleet(String holat) {
        return switch (holat == null ? "" : holat) {
            case "yangi" -> QUEUED;
            case "tayinlandi" -> ASSIGNED;
            case "yolda" -> ON_THE_WAY;
            case "yetib_keldi" -> ARRIVED;
            case "topshirildi" -> DELIVERED;
            case "qaytarildi" -> RETURNED;
            case "bekor" -> CANCELLED;
            default -> throw new IllegalArgumentException("Noma'lum flot holati: " + holat);
        };
    }
}
