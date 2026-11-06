require "ipaddr"
require "yaml"

abort "Usage: ruby scripts/convert_anthropic.rb SOURCE.yaml" unless ARGV.length == 1

document = YAML.safe_load(File.read(ARGV.first, encoding: "bom|utf-8"))
rules = document["payload"] if document.is_a?(Hash)
abort "Expected a non-empty YAML payload array" unless rules.is_a?(Array) && !rules.empty?

converted = rules.map.with_index(1) do |rule, index|
  fields = rule.is_a?(String) ? rule.split(",", -1).map(&:strip) : []
  type, value, option = fields
  valid = case type
          when "DOMAIN", "DOMAIN-SUFFIX", "DOMAIN-KEYWORD"
            fields.length == 2 && value.match?(/\A[a-z0-9_.-]+\z/i)
          when "PROCESS-NAME"
            fields.length == 2 && value.match?(/\A[^[:cntrl:]"]+\z/)
          when "IP-CIDR", "IP-CIDR6", "IP-ASN"
            valid_option = fields.length == 2 || (fields.length == 3 && option == "no-resolve")
            valid_option && if type == "IP-ASN"
              value.match?(/\A[0-9]+\z/) && value.to_i.between?(1, 4_294_967_295)
            else
              address = IPAddr.new(value) if value.match?(%r{\A[0-9a-f:.]+/[0-9]+\z}i)
              address && (type == "IP-CIDR" ? address.ipv4? : address.ipv6?)
            end
          end
  abort "Unsupported or malformed payload entry #{index}: #{rule.inspect}" unless valid

  fields.join(",")
rescue IPAddr::Error
  abort "Invalid CIDR at payload entry #{index}: #{rule.inspect}"
end

puts "# Generated from jinxinkai/clash-ai-rules/Anthropic.yaml (master branch)"
puts "# Upstream license: MIT (https://github.com/jinxinkai/clash-ai-rules/blob/master/README.md#license)"
puts converted
