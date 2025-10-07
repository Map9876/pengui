

# pengui
https://github.com/LNRelease/lnrelease.github.io

您说得对！对于GET请求，参数确实可以跟在URL后面的`?`和`&`后面。让我给您完整的GET请求链接：

## 1. 获取nonce的GET请求链接（这个本来就是GET）
```
https://prhcomics.com/wp/wp-admin/admin-ajax.php?action=get_nonce
```

## 2. 产品列表请求转换为GET的完整链接

**基础URL:**
```
https://prhcomics.com/wp/wp-admin/admin-ajax.php
```

**带所有参数的完整GET链接（需要替换nonce值）：**
```
https://prhcomics.com/wp/wp-admin/admin-ajax.php?action=get_product_list&product_load_nonce=YOUR_NONCE_HERE&postType=page&postId=11538&isbns=[]&filters={"l1_category":"all-categories-manga","filters":{"category":[],"sale-status":[{"label":"Coming Soon","filterId":"sale-status","key":"onSaleFrom","value":"tomorrow"}],"format":[],"age":[],"grade":[],"guides":[],"publisher":[],"comics_publisher":[]}}&layout=grid-lg&start=0&rows=36&sort=frontlistiest_onsale:desc&params={"source-page":"category-landing-page"}
```

**注意：** 由于filters参数包含特殊字符，您可能需要先URL编码。这里是URL编码后的版本：

```
https://prhcomics.com/wp/wp-admin/admin-ajax.php?action=get_product_list&product_load_nonce=YOUR_NONCE_HERE&postType=page&postId=11538&isbns=%5B%5D&filters=%7B%22l1_category%22%3A%22all-categories-manga%22%2C%22filters%22%3A%7B%22category%22%3A%5B%5D%2C%22sale-status%22%3A%5B%7B%22label%22%3A%22Coming%20Soon%22%2C%22filterId%22%3A%22sale-status%22%2C%22key%22%3A%22onSaleFrom%22%2C%22value%22%3A%22tomorrow%22%7D%5D%2C%22format%22%3A%5B%5D%2C%22age%22%3A%5B%5D%2C%22grade%22%3A%5B%5D%2C%22guides%22%3A%5B%5D%2C%22publisher%22%3A%5B%5D%2C%22comics_publisher%22%3A%5B%5D%7D%7D&layout=grid-lg&start=0&rows=36&sort=frontlistiest_onsale%3Adesc&params=%7B%22source-page%22%3A%22category-landing-page%22%7D
```

## 3. 测试步骤

1. **首先获取nonce：**
   ```
   https://prhcomics.com/wp/wp-admin/admin-ajax.php?action=get_nonce
   ```

https://c.map987.dpdns.org/https%3A%2F%2Fprhcomics.com%2Fwp%2Fwp-admin%2Fadmin-ajax.php%3Faction%3Dget_nonce

响应：

```json
{"nonce":"70d745f0ce","nonceNewsletter":"e3839ef2ad","nonceFilters":"1b970105ea","nonceDownloads":"e8fce2f88e"}
```

2. **复制nonce值**，替换下面链接中的`YOUR_NONCE_HERE`

3. **测试产品列表请求：**
   ```
   https://prhcomics.com/wp/wp-admin/admin-ajax.php?action=get_product_list&product_load_nonce=YOUR_ACTUAL_NONCE&postType=page&postId=11538&isbns=[]&filters={"l1_category":"all-categories-manga","filters":{"category":[],"sale-status":[{"label":"Coming Soon","filterId":"sale-status","key":"onSaleFrom","value":"tomorrow"}],"format":[],"age":[],"grade":[],"guides":[],"publisher":[],"comics_publisher":[]}}&layout=grid-lg&start=0&rows=36&sort=frontlistiest_onsale:desc&params={"source-page":"category-landing-page"}
   ```

## 4. 直接在浏览器中测试

您可以直接在浏览器地址栏中输入这些链接来测试。不过要注意：

- 第一个链接（获取nonce）应该能正常工作
- 第二个链接可能需要先获取有效的nonce值
- 如果服务器要求POST请求，GET可能会失败

**简单测试方法：**
```python
import requests
import webbrowser

# 获取nonce
nonce_url = "https://prhcomics.com/wp/wp-admin/admin-ajax.php?action=get_nonce"
response = requests.get(nonce_url)
nonce = response.json()['nonce']
print(f"获取到的nonce: {nonce}")

# 构建产品列表GET链接
product_url = f"https://prhcomics.com/wp/wp-admin/admin-ajax.php?action=get_product_list&product_load_nonce={nonce}&postType=page&postId=11538&isbns=[]&layout=grid-lg&start=0&rows=36&sort=frontlistiest_onsale:desc"

print(f"产品列表链接: {product_url}")

# 在浏览器中打开（可选）
webbrowser.open(product_url)
```

现在您可以直接点击或复制这些完整的链接到浏览器中测试了！
