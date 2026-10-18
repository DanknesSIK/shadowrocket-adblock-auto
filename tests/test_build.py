import unittest
from build import accepts, assemble, mitm_hosts, parse_qx, parse_shadowrocket, protected

class BuilderTests(unittest.TestCase):
    def test_domain_protection(self):
        self.assertTrue(protected("DOMAIN,login.openai.com,REJECT", ["openai.com"]))
        self.assertTrue(protected(r"^https?:\/\/pay\.alipay\.com", ["alipay.com"]))
        self.assertFalse(protected("DOMAIN,notopenai.com,REJECT", ["openai.com"]))

    def test_rules_are_reject_only(self):
        cfg = {"protected_domain_suffixes": ["qq.com"]}
        self.assertTrue(accepts("Rule", "DOMAIN,ads.test.com,REJECT", cfg))
        self.assertFalse(accepts("Rule", "DOMAIN,ads.test.com,DIRECT", cfg))
        self.assertFalse(accepts("Rule", "DOMAIN,wx.qq.com,REJECT", cfg))
        self.assertTrue(accepts("URL Rewrite", r"^https:\/\/ads\.test\.com\/ad - reject", cfg))
        self.assertFalse(accepts("URL Rewrite", r"^https:\/\/ads\.test\.com\/ad - rewrite https://evil.test", cfg))

    def test_qx_subset(self):
        data = r"hostname = api.zhihu.com" + "\n" + r"^https?:\/\/api\.zhihu\.com\/splash url reject" + "\n"
        parsed, unused = parse_qx(data)
        self.assertEqual(unused, 0)
        self.assertEqual(len(parsed["URL Rewrite"]), 1)
        self.assertEqual(len(parsed["MITM"]), 1)

    def test_aggregate(self):
        cfg = {"settings": {
            "name":"Test","description":"Test","include_rules":True,
            "include_url_rewrite":True,"include_body_rewrite":True,
            "include_remote_scripts":False,"include_header_rewrite":False,"include_map_local":False,
            "mitm_selected_suffixes":["zhihu.com"],
            "protected_domain_suffixes":["openai.com","qq.com"],
            "max_output_bytes":200000,"min_output_rules":2},
            "sources":[{"id":"test","enabled":True,"format":"shadowrocket","url":"https://example.com"}]}
        content = """[Rule]
DOMAIN,ads.zhihu.com,REJECT
DOMAIN,ads.zhihu.com,REJECT
DOMAIN,openai.com,REJECT
[URL Rewrite]
^https://api.zhihu.com/ad - reject
[Script]
xyz = type=http-response, script-path=https://evil.com/script.js
[MITM]
hostname = %APPEND% api.zhihu.com,qq.com,*.openai.com
"""
        module, report = assemble(cfg, {"test":(content,"abc")})
        self.assertEqual(module.count("DOMAIN,ads.zhihu.com,REJECT"), 1)
        self.assertNotIn("DOMAIN,openai.com", module)
        self.assertNotIn("script-path=", module)
        self.assertIn("api.zhihu.com", module)
        self.assertNotIn("qq.com", module)
        self.assertEqual(report["total_rules"], 2)

if __name__ == "__main__":
    unittest.main()
