
# 这个skill的目的

这个skill是为了挑战上限，就是不依赖第三方联网搜索mcp，自己通过实现skill，提供给agent实现联网搜索和url详情内容提取。

实际上第三方免费联网搜索mcp质量很差，真的就是免费没好货，想要稳定自己就要花钱买优质搜索引擎大厂的联网搜索apikey才行。

用户可以两者结合，使用`anysearch`每天免费1000次额度，或者非常不稳定的 `open-web-search` 等免费mcp； 并且搭配用户自己写的联网搜索skill，共同实现联网搜索发现网站url和对url内容提取。

# 如果不实现这个skill还想用百度
那么你需要去百度千帆购买百度mcp搜索的apikey， https://cloud.baidu.com/doc/qianfan/s/2mh4su4uy     搜一次关键词收费大约0.03元，这个天价完全扛不住，有了这个skill每天搜索几千次节约下上百元真金白银。


# 通过百度接口实现的联网检索 skill。

类似anyserch的skill用法， ai大模型使用skill里面的脚本，联网，但是不要钱，无限免费。

默认使用的了curl_cffi来请求url，而不是requests，这样不触发反扒。

这个不打算做成tools装饰器方式，而是直接采用skill方式就可以了。


## 说明：

### 对特定网站抓取url内容的策略需要用户自己去在`references` 增加提示词。

虽然skill搞定了百度的搜索页，搞定了根据关键字找到详情页url和摘要。但是部分url网页用简单常规的使用extract_url的 http请求主网页url方式拿不到正文，例如有的是反扒，有的是正文需要ajax请求中，有的需要逆向破解请求入参，所以对于用户需要常用的频繁且直接http请求url拿不到正文的网站，用文可以自行在 `references` 文件夹中补充抓取某个网站url内容的策略。 

为什么要放到 `references` 文件夹中呢，这是为了保持主skill长度小，采用多层渐进式发现提示词。
如果把所有针对特定网站url的抓取策略写到skill，那太费上下文了，违背 `agentskills.io` 的国际协议。

#### 例如对于知乎网站的url
例如对于知乎网站的url怎么获取，教会llm的skill提示词就在 `references/zhihu-browser-access.md` ,这个需要用户安装 agent-browser skill，并且教会llm怎么点击浏览器元素获取更多回答内容。

知乎回答就是普通http请求不到，因为官方不想被人轻松爬取，如果你不信，你可以给个知乎问答的url，让deepseek app根据知乎url总结正文内容，deepseek一样获取不到知乎回答详情。