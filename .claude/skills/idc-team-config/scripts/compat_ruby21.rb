# frozen_string_literal: true

require "yaml"

# IDC supports enterprise hosts pinned to Ruby 2.1. Newer Rubies already provide
# these APIs, so every shim is guarded and becomes a no-op there.
class Hash
  unless method_defined?(:dig)
    def dig(key, *identifiers)
      value = self[key]
      return value if value.nil? || identifiers.empty?
      raise TypeError, "#{value.class} does not have #dig method" unless value.respond_to?(:dig)
      value.dig(*identifiers)
    end
  end

  unless method_defined?(:transform_values)
    def transform_values
      return enum_for(:transform_values) unless block_given?
      each_with_object({}) { |(key, value), result| result[key] = yield(value) }
    end
  end
end

class Array
  unless method_defined?(:dig)
    def dig(index, *identifiers)
      value = self[index]
      return value if value.nil? || identifiers.empty?
      raise TypeError, "#{value.class} does not have #dig method" unless value.respond_to?(:dig)
      value.dig(*identifiers)
    end
  end
end

class String
  unless method_defined?(:match?)
    def match?(pattern)
      !match(pattern).nil?
    end
  end

  unless method_defined?(:delete_prefix)
    def delete_prefix(prefix)
      start_with?(prefix) ? self[prefix.length..-1] : dup
    end
  end
end

class Numeric
  unless method_defined?(:negative?)
    def negative?
      self < 0
    end
  end
end

class Object
  unless method_defined?(:itself)
    def itself
      self
    end
  end
end

module IDCRubyCompat
  def self.safe_yaml_load(source)
    YAML.safe_load(source, [], [], false)
  end
end
