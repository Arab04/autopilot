package com.example.CRM.sale.repository;

import com.example.CRM.sale.entity.SaleEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;

@Repository
public interface SaleRepository extends JpaRepository<SaleEntity, Long> {

    @Query(value = "select coalesce(sum(total),0) from sales where date(created_at)=:d", nativeQuery = true)
    BigDecimal todayTotal(LocalDate d);

    @Query(value = "select count(*) from products where active=true", nativeQuery = true)
    long activeProducts();

    @Query(value = """
    select si.product_id, sum(si.line_total) as revenue
    from sale_items si join sales s on s.id=si.sale_id
    where s.status='PAID'
    group by si.product_id
    order by revenue desc
    limit 5
  """, nativeQuery = true)
    List<Object[]> top5ProductsByRevenue();
}
