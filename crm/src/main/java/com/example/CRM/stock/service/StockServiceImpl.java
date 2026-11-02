package com.example.CRM.stock.service;

import com.example.CRM.product.entity.ProductEntity;
import com.example.CRM.product.repository.ProductRepository;
import com.example.CRM.stock.dto.StockUpsertRequest;
import com.example.CRM.stock.entity.StockEntity;
import com.example.CRM.stock.repository.StockRepository;
import com.example.CRM.warehouse.entity.WarehouseEntity;
import com.example.CRM.warehouse.repository.WarehouseRepository;
import jakarta.persistence.EntityNotFoundException;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
@RequiredArgsConstructor
public class StockServiceImpl implements StockService {

    private final StockRepository stockRepo;
    private final ProductRepository productRepo;
    private final WarehouseRepository warehouseRepo;

    @Override
    public StockEntity upsert(StockUpsertRequest req) {
        ProductEntity product = productRepo.findById(req.productId())
                .orElseThrow(() -> new EntityNotFoundException("Product not found"));
        WarehouseEntity wh = warehouseRepo.findById(req.warehouseId())
                .orElseThrow(() -> new EntityNotFoundException("Warehouse not found"));

        StockEntity stock = stockRepo.findByProduct_IdAndWarehouse_Id(req.productId(), req.warehouseId())
                .orElse(StockEntity.builder().product(product).warehouse(wh).quantity(0).build());

        stock.setQuantity(req.quantity());
        return stockRepo.save(stock);
    }

    @Override
    public List<StockEntity> listByWarehouse(Long warehouseId) {
        return stockRepo.listByWarehouse(warehouseId);
    }
}
