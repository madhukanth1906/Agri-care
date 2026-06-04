# Frontend Deployment Guide

This document provides instructions for deploying the AgriCare frontend application.

## Deployment Options

### Option 1: Static Hosting (Recommended)

The frontend is a static application that can be hosted on any static hosting service:

#### Netlify
1. Create account at [netlify.com](https://netlify.com)
2. Drag and drop the `frontend` folder to Netlify dashboard
3. Configure custom domain if needed
4. Set up continuous deployment from Git repository

#### Vercel
1. Install Vercel CLI: `npm i -g vercel`
2. Navigate to frontend directory: `cd frontend`
3. Run: `vercel`
4. Follow the prompts

#### GitHub Pages
1. Push frontend files to a GitHub repository
2. Go to repository Settings > Pages
3. Select source branch and folder
4. Access via `https://username.github.io/repository-name`

### Option 2: Traditional Web Hosting

Upload the `frontend` folder contents to your web hosting provider's public directory (usually `public_html` or `www`).

### Option 3: Express.js Static Serving

The backend already includes static file serving. Simply:
1. Deploy the backend to a cloud service
2. Access the frontend via your backend URL

## Configuration for Production

### 1. Update API Configuration

In `frontend/js/config.js`, update the API base URL:

```javascript
const API_CONFIG = {
    BASE_URL: 'https://your-backend-domain.com', // Replace with your backend URL
    TIMEOUT: 30000,
    RETRY_ATTEMPTS: 3
};
```

### 2. Environment Variables

For sensitive configuration, you can use environment variables:

```javascript
const API_CONFIG = {
    BASE_URL: process.env.REACT_APP_API_URL || 'http://localhost:3000',
    TIMEOUT: 30000,
    RETRY_ATTEMPTS: 3
};
```

### 3. Performance Optimization

#### Enable Gzip Compression
Most hosting providers enable this automatically. For custom servers:

```nginx
# Nginx configuration
gzip on;
gzip_types text/css application/javascript application/json;
```

#### Set Caching Headers
```nginx
# Cache static assets
location ~* \.(css|js|png|jpg|jpeg|gif|svg|ico)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

### 4. Security Configuration

#### Content Security Policy
Add to your HTML head:

```html
<meta http-equiv="Content-Security-Policy" content="
    default-src 'self';
    script-src 'self' 'unsafe-inline' cdnjs.cloudflare.com;
    style-src 'self' 'unsafe-inline' cdnjs.cloudflare.com fonts.googleapis.com;
    font-src 'self' fonts.gstatic.com;
    img-src 'self' data: https:;
    connect-src 'self' https://api.accuweather.com https://generativelanguage.googleapis.com;
">
```

## Build Process (Optional)

For advanced optimization, you can create a build process:

### 1. Install Build Tools

```bash
npm install -g html-minifier clean-css-cli uglify-js
```

### 2. Create Build Script

Create `build.js`:

```javascript
const fs = require('fs');
const htmlMinifier = require('html-minifier');
const CleanCSS = require('clean-css');
const UglifyJS = require('uglify-js');

// Minify HTML
const html = fs.readFileSync('index.html', 'utf8');
const minifiedHtml = htmlMinifier.minify(html, {
    removeComments: true,
    removeRedundantAttributes: true,
    removeScriptTypeAttributes: true,
    removeStyleLinkTypeAttributes: true,
    sortClassName: true,
    useShortDoctype: true,
    collapseWhitespace: true
});
fs.writeFileSync('dist/index.html', minifiedHtml);

// Minify CSS
const css = fs.readFileSync('css/styles.css', 'utf8');
const minifiedCss = new CleanCSS().minify(css).styles;
fs.writeFileSync('dist/css/styles.min.css', minifiedCss);

// Minify JavaScript
const jsFiles = ['js/app.js', 'js/auth.js', 'js/weather.js', 'js/disease.js', 'js/yield.js', 'js/chatbot.js'];
jsFiles.forEach(file => {
    const js = fs.readFileSync(file, 'utf8');
    const minified = UglifyJS.minify(js);
    const outputFile = file.replace('.js', '.min.js').replace('js/', 'dist/js/');
    fs.writeFileSync(outputFile, minified.code);
});
```

### 3. Run Build

```bash
node build.js
```

## Monitoring and Analytics

### 1. Google Analytics
Add to your HTML head:

```html
<!-- Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id=GA_TRACKING_ID"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'GA_TRACKING_ID');
</script>
```

### 2. Error Tracking

Add error tracking with Sentry:

```html
<script src="https://browser.sentry-cdn.com/7.x.x/bundle.min.js"></script>
<script>
  Sentry.init({ dsn: 'YOUR_SENTRY_DSN' });
</script>
```

## Domain and SSL

### 1. Custom Domain
- Purchase domain from registrar
- Point DNS to your hosting provider
- Configure domain in hosting dashboard

### 2. SSL Certificate
Most hosting providers offer free SSL certificates:
- Netlify: Automatic HTTPS
- Vercel: Automatic HTTPS
- Traditional hosting: Let's Encrypt or paid certificates

## Troubleshooting

### Common Issues

1. **CORS Errors**
   - Ensure backend CORS is configured correctly
   - Check API_CONFIG.BASE_URL is correct

2. **API Connection Failed**
   - Verify backend is running and accessible
   - Check network connectivity
   - Verify API endpoints are correct

3. **Static Assets Not Loading**
   - Check file paths are relative
   - Verify files are uploaded correctly
   - Check server configuration

### Debug Mode

Enable debug mode by adding to localStorage:
```javascript
localStorage.setItem('agricare_debug', 'true');
```

## Performance Checklist

- [ ] Minify HTML, CSS, and JavaScript
- [ ] Optimize images (WebP format, compression)
- [ ] Enable gzip compression
- [ ] Set proper caching headers
- [ ] Use CDN for static assets
- [ ] Implement lazy loading for images
- [ ] Monitor Core Web Vitals

## Backup and Recovery

### 1. Regular Backups
- Keep source code in version control (Git)
- Backup configuration files
- Document deployment process

### 2. Recovery Plan
- Maintain staging environment
- Keep rollback procedures documented
- Monitor application health

---

This guide covers the essential steps for deploying the AgriCare frontend. Choose the deployment option that best fits your needs and infrastructure.