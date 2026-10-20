package com.example.CRM.dashboard;

import com.example.CRM.sale.repository.SaleRepository;
import com.example.CRM.stock.repository.StockRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/reports")
@RequiredArgsConstructor
public class ReportsController {

    private final SaleRepository saleRepo;
    private final StockRepository stockRepo;

    @GetMapping("/dashboard")
    public Map<String, Object> dashboard() {
        BigDecimal today = saleRepo.todayTotal(LocalDate.now());
        long activeProducts = saleRepo.activeProducts();

        return Map.of(
                "todaySales", today,
                "activeProducts", activeProducts
        );
    }

    @GetMapping("/top5-products")
    public List<Map<String, Object>> top5() {
        List<Object[]> rows = saleRepo.top5ProductsByRevenue();
        List<Map<String, Object>> res = new ArrayList<>();
        for (Object[] r : rows) {
            res.add(Map.of(
                    "productId", r[0],
                    "revenue", r[1]
            ));
        }
        return res;
    }
}
