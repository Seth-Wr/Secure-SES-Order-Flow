// ============================================
// SUCCESS PAGE INITIALIZATION
// ============================================

/**
 * Extract order ID from URL query parameters
 * Expected URL format: success.html?orderId=ABC12345
 */
function getOrderIdFromUrl() {
  const urlParams = new URLSearchParams(window.location.search);
  return urlParams.get('orderId');
}

/**
 * Display the order ID on the page
 * Falls back to a message if no order ID is found
 */
function displayOrderId() {
  const orderId = getOrderIdFromUrl();
  const orderIdElement = document.getElementById('orderId');
  
  if (orderId) {
    orderIdElement.textContent = orderId;
  } else {
    // Fallback if no order ID in URL
    orderIdElement.textContent = 'Check your email';
    console.warn('No order ID found in URL parameters');
  }
}

/**
 * Clear the shopping cart from localStorage
 * Called after successful order completion
 */
function clearCart() {
  try {
    localStorage.removeItem('cart');
    console.log('Cart cleared successfully');
  } catch (error) {
    console.error('Error clearing cart:', error);
  }
}

// ============================================
// INITIALIZATION
// ============================================

// Run when page loads
displayOrderId();
clearCart();