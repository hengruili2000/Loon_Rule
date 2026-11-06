require "yaml"

abort "Usage: ruby scripts/convert_category_ai_non_cn.rb SOURCE.yaml [UPSTREAM_NAME]" unless (1..2).cover?(ARGV.length)

name = ARGV.fetch(1, "category-ai-!cn")
abort "Invalid upstream rule name" unless /\A[a-z0-9!-]+\z/.match?(name)

document = YAML.safe_load(File.read(ARGV.first, encoding: "bom|utf-8"))
payload = document["payload"] if document.is_a?(Hash)
abort "Expected a non-empty YAML payload array" unless payload.is_a?(Array) && !payload.empty?

domain_pattern = /\A[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)*\z/i
converted = payload.map.with_index(1) do |entry, index|
  abort "Expected a domain string at payload entry #{index}" unless entry.is_a?(String)

  suffix = entry.start_with?("+.")
  domain = suffix ? entry[2..-1] : entry
  abort "Unsupported domain pattern at payload entry #{index}: #{entry.inspect}" unless domain_pattern.match?(domain)

  "#{suffix ? "DOMAIN-SUFFIX" : "DOMAIN"},#{domain}"
end

puts "# Generated from MetaCubeX/meta-rules-dat/geo/geosite/#{name}.yaml (meta branch)"
puts "# Upstream license: GPL-3.0. See category-ai-!cn.LICENSE."
puts converted
