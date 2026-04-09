<?php
/**
 * Plugin Name: SmartCounter Connector
 * Description: Emisor de eventos en tiempo real para SmartWork (Anti-Stock Fantasma & Conciliación).
 * Version: 1.0.0
 * Author: SmartWork
 */

if (!defined('ABSPATH'))
    exit;

// CONFIG
define('SC_BACKEND_URL', 'https://tu-api-smartwork.com/module-ingestions');
define('SC_TENANT_ID', 'woo_real_001');

/**
 * Core sender
 */
function sc_send_to_smartwork($module, $data)
{
    $payload = [
        "tenant_id" => SC_TENANT_ID,
        "module" => $module,
        "source_type" => "woocommerce",
        "generated_at" => gmdate('c'),
        "canonical_rows" => [$data],
        "findings" => [],
        "summary" => (object) [],
        "suggested_actions" => []
    ];

    wp_remote_post(SC_BACKEND_URL, [
        'method' => 'POST',
        'timeout' => 10,
        'headers' => ['Content-Type' => 'application/json'],
        'body' => json_encode($payload),
        'blocking' => false,
    ]);
}

/**
 * 1. ORDER PAID
 */
add_action('woocommerce_payment_complete', function ($order_id) {
    $order = wc_get_order($order_id);
    if (!$order)
        return;

    sc_send_to_smartwork('woocommerce_orders', [
        'order_id' => (string) $order_id,
        'total' => (float) $order->get_total(),
        'currency' => $order->get_currency(),
        'payment_method' => $order->get_payment_method(),
        'created_at' => $order->get_date_created()->date('c'),
        'customer_id' => $order->get_customer_id(),
        'action' => 'paid'
    ]);
});

/**
 * 2. STATUS CHANGE
 */
add_action('woocommerce_order_status_changed', function ($order_id, $old_status, $new_status) {
    sc_send_to_smartwork('woocommerce_status_monitor', [
        'order_id' => (string) $order_id,
        'old_status' => $old_status,
        'new_status' => $new_status,
        'updated_at' => gmdate('c')
    ]);
}, 10, 3);

/**
 * 3. STOCK CHANGE
 */
add_action('woocommerce_reduce_order_stock', function ($order) {
    foreach ($order->get_items() as $item) {
        $product = $item->get_product();
        if ($product && $product->managing_stock()) {
            sc_send_to_smartwork('woocommerce_stock_sync', [
                'product_id' => (string) $product->get_id(),
                'sku' => $product->get_sku(),
                'quantity' => $item->get_quantity(),
                'stock_after' => $product->get_stock_quantity(),
                'event' => 'inventory_reduction'
            ]);
        }
    }
});