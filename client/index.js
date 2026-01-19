// ============================================
// DOM ELEMENT REFERENCES
// ============================================
const orderButtons = document.querySelectorAll(".order-btn");
const productNames = document.querySelectorAll(".product-name");
const productPrices = document.querySelectorAll(".price");
const productImages = document.querySelectorAll(".product-img");
const shoppingBagQty = document.querySelector(".shopping-bag-qty");
const toastContainer = document.querySelector(".toast-container");
const toastMsg = document.querySelector(".toast-msg");

// ============================================
// CART CLASS
// ============================================
class Cart {
  constructor(existingCart = {}) {
    this.items = existingCart.items || {};
    this.totalQty = existingCart.totalQty || 0;
    this.totalPrice = existingCart.totalPrice || 0;
  }

  addItem(productName, pricePerUnit, imageUrl) {
    let item = this.items[productName];
    
    if (!item) {
      item = this.items[productName] = {
        qty: 0,
        price: 0,
        pricePerUnit: 0,
        imageUrl: imageUrl
      };
    }

    item.pricePerUnit = pricePerUnit;
    item.qty++;
    item.price = item.pricePerUnit * item.qty;

    this.totalPrice += pricePerUnit;
    this.totalQty++;

    return this;
  }
}

// ============================================
// STORAGE UTILITIES
// ============================================
const StorageManager = {
  /**
   * Set an item in localStorage
   * @param {string} key - Storage key
   * @param {*} value - Value to store (will be stringified)
   */
  set(key, value) {
    try {
      const stringValue = typeof value === 'string' ? value : JSON.stringify(value);
      localStorage.setItem(key, stringValue);
    } catch (error) {
      console.error('Error saving to localStorage:', error);
    }
  },

  /**
   * Get an item from localStorage
   * @param {string} key - Storage key
   * @returns {string|null} - Stored value or null if not found
   */
  get(key) {
    try {
      return localStorage.getItem(key);
    } catch (error) {
      console.error('Error reading from localStorage:', error);
      return null;
    }
  },

  /**
   * Remove an item from localStorage
   * @param {string} key - Storage key
   */
  remove(key) {
    try {
      localStorage.removeItem(key);
    } catch (error) {
      console.error('Error removing from localStorage:', error);
    }
  },

  /**
   * Check if cart exists and update UI
   * @param {string} key - Storage key to check
   */
  checkAndUpdateUI(key) {
    const cartData = this.get(key);
    
    if (cartData) {
      const cart = JSON.parse(cartData);
      
      shoppingBagQty.textContent = cart.totalQty;
      
      if (cart.totalQty > 0) {
        shoppingBagQty.classList.add("active");
      } else {
        shoppingBagQty.classList.remove("active");
      }
    } else {
      shoppingBagQty.classList.remove("active");
    }
  }
};

// ============================================
// UI UTILITIES
// ============================================
const UIManager = {
  /**
   * Show a toast notification
   * @param {string} message - Message to display
   * @param {number} duration - How long to show (milliseconds)
   */
  showToast(message, duration = 1000) {
    toastMsg.textContent = message;
    toastContainer.classList.add("active");
    
    setTimeout(() => {
      toastContainer.classList.remove("active");
    }, duration);
  },

  /**
   * Update the shopping bag quantity badge
   * @param {number} quantity - Number to display
   */
  updateCartBadge(quantity) {
    shoppingBagQty.textContent = quantity;
    shoppingBagQty.classList.add("active");
  },
};

// ============================================
// CART OPERATIONS
// ============================================
const CartManager = {
  /**
   * Get the current cart from localStorage
   * @returns {Cart} - Cart instance
   */
  getCart() {
    const cartData = StorageManager.get('cart');
    const existingCart = cartData ? JSON.parse(cartData) : {};
    return new Cart(existingCart);
  },

  /**
   * Save cart to localStorage
   * @param {Cart} cart - Cart instance to save
   */
  saveCart(cart) {
    const cartString = JSON.stringify(cart);
    StorageManager.set('cart', cartString);
  },

  /**
   * Add product to cart and update UI
   * @param {string} name - Product name
   * @param {number} price - Product price
   * @param {string} imageUrl - Product image URL
   */
  addToCart(name, price, imageUrl) {
    const cart = this.getCart();
    cart.addItem(name, price, imageUrl);
    this.saveCart(cart);
    
    UIManager.updateCartBadge(cart.totalQty);
    UIManager.showToast(`${name} has been added to your cart`);
  }
};

// ============================================
// UTILITY FUNCTIONS
// ============================================
function parsePrice(priceText) {
  return parseFloat(priceText.replace('$', ''));
}

function formatPrice(value) {
  return `$${value.toFixed(2)}`;
}

// ============================================
// EVENT LISTENERS
// ============================================
orderButtons.forEach((btn, index) => {
  btn.addEventListener('click', () => {
    const name = productNames[index].textContent;
    const price = parsePrice(productPrices[index].textContent);
    const imageUrl = productImages[index].src;
    
    CartManager.addToCart(name, price, imageUrl);
  });
});

// ============================================
// INITIALIZATION
// ============================================
StorageManager.checkAndUpdateUI('cart');

window.addEventListener('pageshow', (event) => {
  if (event.persisted) {
    StorageManager.checkAndUpdateUI('cart');
  }
});