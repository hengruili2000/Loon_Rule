require "yaml"

abort "Usage: ruby scripts/convert_custom_us_proxy.rb SOURCE.yaml" unless ARGV.length == 1

document = YAML.safe_load(File.read(ARGV.first, encoding: "bom|utf-8"))
rules = document["payload"] if document.is_a?(Hash)
abort "Expected a non-empty YAML payload array" unless rules.is_a?(Array) && !rules.empty?

supported_types = %w[DOMAIN DOMAIN-SUFFIX DOMAIN-KEYWORD]
converted = rules.map.with_index(1) do |rule, index|
  fields = rule.is_a?(String) ? rule.split(",", -1).map(&:strip) : []
  type, value = fields
  unless fields.length == 2 && supported_types.include?(type) && value.match?(/\A[a-z0-9_.-]+\z/i)
    abort "Unsupported or malformed payload entry #{index}: #{rule.inspect}"
  end

  "#{type},#{value}"
end

puts "# Generated from hengruili2000/Custom_OpenClash_Rules/rule/Custom_US_Proxy.yaml"
puts converted
