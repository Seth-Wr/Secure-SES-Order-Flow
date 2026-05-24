function handler(event) {
    var request = event.request;
    var uri = request.uri;
    
    // 1. If it ends in a slash, add index.html
    if (uri.endsWith('/')) {
        request.uri += 'index.html';
    } 
    // 2. If it doesn't have a dot (likely a sub-route), add /index.html
    // This supports Single Page Apps (SPA) like React or Vue
    else if (!uri.includes('.')) {
        request.uri += '/index.html';
    }
    
    return request;
}
