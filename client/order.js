// ============================================
// DOM ELEMENT REFERENCES
// ============================================
const shoppingBagQty = document.querySelector(".shopping-bag-qty");
const orderContainer = document.querySelector(".order");
const totalQtyElement = document.querySelector(".total-qty");
const checkoutPriceElement = document.querySelector(".checkout-price");
const emailInput = document.querySelector(".email-input");
const numberInput = document.querySelector(".number-input");
const verificationInput = document.querySelector(".verification-input")
const shippingInput = document.querySelector(".shipping-input");
const aptNumberInput = document.querySelector(".apt-num-input");
const checkoutBtn = document.querySelector(".checkout-btn");
const errorMsg = document.querySelector(".error-msg");
const loader = document.querySelector(".loader-container");

// ============================================
// CONSTANTS
// ============================================
const PHONE_PATTERN = /^(\+?1 *[ -.])?(\d{3}) *[ .-]?(\d{3}) *[ .-]?(\d{4}) *$/;
const EMAIL_PATTERN = /^[a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;

// ============================================
// CART CLASS
// ============================================
class Cart {
  constructor(existingCart = {}) {
    this.items = existingCart.items || {};
    this.totalQty = existingCart.totalQty || 0;
    this.totalPrice = existingCart.totalPrice || 0;
  }

  updateQuantity(itemName, newQty) {
    const item = this.items[itemName];
    if (!item) return;

    const qtyDifference = newQty - item.qty;
    const priceDifference = qtyDifference * item.pricePerUnit;

    item.qty = newQty;
    item.price = item.pricePerUnit * newQty;

    this.totalQty += qtyDifference;
    this.totalPrice += priceDifference;
  }

  removeItem(itemName) {
    const item = this.items[itemName];
    if (!item) return;

    this.totalPrice -= item.price;
    this.totalQty -= item.qty;

    delete this.items[itemName];
  }
  toPlainObject() {
    return {
      items: this.items, // Ensure these are simple {qty, price, etc.} objects
      totalQty: this.totalQty,
      totalPrice: this.totalPrice
    };
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
  }
};

// ============================================
// CART MANAGER
// ============================================
const CartManager = {
  /**
   * Get cart from localStorage
   * @returns {Cart|null} - Cart instance or null
   */
  getCart() {
    const cartData = StorageManager.get('cart');
    if (!cartData) return null;
    
    const cartObj = JSON.parse(cartData);
    return new Cart(cartObj);
  },

  /**
   * Save cart to localStorage
   * @param {Cart} cart - Cart to save
   */
  saveCart(cart) {
    const cartString = JSON.stringify(cart);
    StorageManager.set('cart', cartString);
  },

  /**
   * Clear cart completely
   */
  clearCart() {
    StorageManager.remove('cart');
  }
};

// ============================================
// UTILITY FUNCTIONS
// ============================================
function formatCurrency(amount) {
  return `$${amount.toFixed(2)}`;
}

function showError(message) {
  errorMsg.textContent = message;
  errorMsg.classList.add('active');
  errorMsg.scrollIntoView({ behavior: "smooth" });
}

function toggleLoader(show) {
  if (show) {
    loader.classList.add('active');
  } else {
    loader.classList.remove('active');
  }
}

// ============================================
// UI RENDERING
// ============================================
function createProductCard(name, price, imageUrl, qty) {
  const showInput = qty >= 10;
  const selectClass = showInput ? 'qty-select' : 'qty-select active';
  const inputClass = showInput ? 'qty-input active' : 'qty-input';

  return `
    <div class="product-card-wrapper">
      <div class="product-card">
        <div class="img-box">
          <img src="${imageUrl}" alt="${name}">
        </div>
        <div class="card-text">
          <h4 class="product-name">${name}</h4>
          <span class="price">${formatCurrency(price)}</span>           
        </div>
        <div class="qty-wrapper">
          <select class="${selectClass}">
            <option value="1">1</option>
            <option value="2">2</option>
            <option value="3">3</option>
            <option value="4">4</option>
            <option value="5">5</option>
            <option value="6">6</option>
            <option value="7">7</option>
            <option value="8">8</option>
            <option value="9">9</option>
            <option value="10">10+</option>
            <option value="${qty}" selected disabled hidden>${qty}</option>
          </select>  
          <input type="number" class="${inputClass}" value="${qty}">
          <button class="remove-btn">remove</button>
        </div>
      </div>
    </div>
  `;
}

function renderCheckoutPage() {
  const cart = CartManager.getCart();

  if (!cart || cart.totalQty === 0) {
    orderContainer.innerHTML = `
      <a href="/" class="homepage-box">
        <button class="homepage">Homepage</button>
      </a>
    `;
    return;
  }

  const productCards = Object.keys(cart.items).map(itemName => {
    const item = cart.items[itemName];
    return createProductCard(itemName, item.price, item.imageUrl, item.qty);
  });

  const html = `<h3>My Order</h3>${productCards.join('')}`;
  orderContainer.innerHTML = html;

  totalQtyElement.textContent = `${cart.totalQty} Items`;
  checkoutPriceElement.textContent = formatCurrency(cart.totalPrice);

  shoppingBagQty.textContent = cart.totalQty;
  shoppingBagQty.classList.add("active");

  attachProductEventListeners();
}

function updateCheckoutUI() {
  const cart = CartManager.getCart();

  if (!cart || cart.totalQty === 0) {
    shoppingBagQty.textContent = '';
    shoppingBagQty.classList.remove("active");
    checkoutPriceElement.textContent = '$0.00';
    totalQtyElement.textContent = '0 Items';
    CartManager.clearCart();
    renderCheckoutPage();
  } else {
    totalQtyElement.textContent = `${cart.totalQty} Items`;
    checkoutPriceElement.textContent = formatCurrency(cart.totalPrice);
    shoppingBagQty.textContent = cart.totalQty;
    shoppingBagQty.classList.add("active");
  }
}

// ============================================
// EVENT HANDLERS
// ============================================
function handleRemoveItem(index, productName) {
  const cart = CartManager.getCart();
  if (!cart) return;

  cart.removeItem(productName);
  CartManager.saveCart(cart);

  const productCards = document.querySelectorAll(".product-card");
  productCards[index].style.display = "none";

  updateCheckoutUI();
}

function handleQuantityChange(index, productName, newQty) {
  const cart = CartManager.getCart();
  if (!cart) return;

  cart.updateQuantity(productName, parseInt(newQty));
  CartManager.saveCart(cart);

  const priceElements = document.querySelectorAll(".price");
  const item = cart.items[productName];
  priceElements[index].textContent = formatCurrency(item.price);

  updateCheckoutUI();
}

function handleQuantityInputToggle(index, qty, isInput) {
  const qtySelects = document.querySelectorAll(".qty-select");
  const qtyInputs = document.querySelectorAll(".qty-input");

  if (isInput && qty < 10) {
    qtyInputs[index].classList.remove("active");
    qtySelects[index].classList.add("active");
    qtySelects[index].value = qty;
  } else if (!isInput && qty >= 10) {
    qtySelects[index].classList.remove("active");
    qtyInputs[index].classList.add("active");
    qtyInputs[index].value = qty;
  }
}

function attachProductEventListeners() {
  const removeButtons = document.querySelectorAll(".remove-btn");
  const qtySelects = document.querySelectorAll(".qty-select");
  const qtyInputs = document.querySelectorAll(".qty-input");
  const productNames = document.querySelectorAll(".product-name");

  removeButtons.forEach((btn, index) => {
    btn.addEventListener('click', () => {
      handleRemoveItem(index, productNames[index].textContent);
    });
  });

  qtySelects.forEach((select, index) => {
    select.addEventListener('change', () => {
      const qty = parseInt(select.value);
      const productName = productNames[index].textContent;
      
      handleQuantityChange(index, productName, qty);
      handleQuantityInputToggle(index, qty, false);
    });
  });

  qtyInputs.forEach((input, index) => {
    input.addEventListener('change', () => {
      const qty = parseInt(input.value);
      const productName = productNames[index].textContent;
      
      handleQuantityChange(index, productName, qty);
      handleQuantityInputToggle(index, qty, true);
    });
  });
}

// ============================================
// SECURE API REQUESTS
// ============================================
async function securePost(path, data) {
  const jsonBody = JSON.stringify(data);
  
  const msgBuffer = new TextEncoder().encode(jsonBody);
  const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer);
  
  const bodyHash = Array.from(new Uint8Array(hashBuffer))
    .map(byte => byte.toString(16).padStart(2, '0'))
    .join('');
  
  return fetch(path, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-amz-content-sha256': bodyHash
    },
    body: jsonBody
  });
}

// ============================================
// CHECKOUT FORM HANDLING
// ============================================
function validatePhone(phone) {
  return PHONE_PATTERN.test(phone);
}

function validateEmail(email) {
  return EMAIL_PATTERN.test(email);
}

async function submitCheckout() {
  const phone = numberInput.value;
  const email = emailInput.value;
  const verification = verificationInput.value
  const shipping = `${shippingInput.value} ${aptNumberInput.value}`.trim();
  const cart = CartManager.getCart();
  
  const turnstileToken = turnstile.getResponse();
  console.log(turnstile.getResponse())

  if (!validatePhone(phone)) {
    showError('Please enter a valid phone number');
    return;
  }

  if (!validateEmail(email)) {
    showError('Please enter a valid email address');
    return;
  }
  
  if (!turnstileToken) {
    showError('Please complete the security check');
    return;
  }

  const checkoutData = {
    phone: phone,
    email: email,
    verification: verification,
    shipping: shipping,
    order: cart.toPlainObject(),
    cf_token: turnstileToken
  };

  try {
    toggleLoader(true);

    const response = await securePost('/api/order', checkoutData);

    if (response.ok) {
      const data = await response.json();
      const orderId = data.orderId;
      
      toggleLoader(false);
      
      // Save order to oldcart for confirmation page
      StorageManager.set('oldcart', cart);
      StorageManager.set('orderId', orderId);

      
      window.location.href = `/success?orderId=${orderId}`;
   } else {
    // 1. Parse the JSON response from the server
    const data = await response.json();
    toggleLoader(false);
    turnstile.reset()

    let errorMessage = 'An error occurred. Please try again.';

    // 2. Check if the server sent a 'detail' field
    if (data.detail) {
        if (Array.isArray(data.detail)) {
            /* This handles 422 Unprocessable Entity errors.
               FastAPI sends an array of objects here. 
               We extract the 'msg' from each and join them.
            */
            errorMessage = data.detail.map(err => err.msg).join('. ');
        } else {
            /* This handles your manual errors like:
               raise HTTPException(status_code=400, detail="Business Closed")
               Here, data.detail is just a simple string.
            */
            errorMessage = data.detail;
        }
    }

    showError(errorMessage);
}
  } catch (error) {
    toggleLoader(false);
    showError('Network error. Please check your connection and try again.');
    turnstile.reset()
    console.error('Checkout error:', error);
  }
}

// ============================================
// EVENT LISTENERS
// ============================================
checkoutBtn.addEventListener('click', submitCheckout);

numberInput.addEventListener('keydown', (e) => {
  const allowedKeys = /[0-9]|Backspace|ArrowLeft|ArrowRight|Enter|Delete|Tab|[ -.]/;
  
  if (!allowedKeys.test(e.key)) {
    e.preventDefault();
  }
});

window.addEventListener('pageshow', (event) => {
  if (event.persisted) {
    renderCheckoutPage();
  }
});

// ============================================
// INITIALIZATION
// ============================================
renderCheckoutPage();
