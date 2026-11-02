package com.example.CRM.stock.repository;

import com.example.CRM.stock.entity.StockEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

import java.util.List;
import java.util.Optional;

public interface StockRepository extends JpaRepository<StockEntity, Long> {

    Optional<StockEntity> findByProduct_IdAndWarehouse_Id(Long productId, Long warehouseId);

    @Query(value = """
    select s.* from stocks s
    where s.warehouse_id = :warehouseId
    order by s.id desc
  """, nativeQuery = true)
    List<StockEntity> listByWarehouse(Long warehouseId);
}
