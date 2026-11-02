package com.example.CRM.auth.entity;

import jakarta.persistence.*;
import lombok.*;

@Entity
@Table(name = "users")
@Getter @Setter @NoArgsConstructor @AllArgsConstructor @Builder
public class UserEntity {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, unique = true, length = 50)
    private String username;

    @Column(nullable = false, length = 255)
    private String password;

    @Column(nullable = false, length = 20)
    private String role; // ADMIN, CLIENT, MERCHANT

    @Column(unique = true, length = 20)
    private String phone;

    @Column(nullable = false)
    private boolean enabled = true;

    @Column(name = "user_type", nullable = false, length = 20)
    private String userType = "CLIENT"; // CLIENT, MERCHANT
}