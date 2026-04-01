using System.Collections.Concurrent;
using System.Text;
using System.Text.Json;
using Grpc.Core;
using Hipstershop;

namespace cartservice;

public class CartServiceImpl : Hipstershop.CartService.CartServiceBase
{
    private readonly ILogger<CartServiceImpl> _logger;
    private readonly OllamaCartAgent _agent;

    public CartServiceImpl(ILogger<CartServiceImpl> logger, OllamaCartAgent agent)
    {
        _logger = logger;
        _agent = agent;
    }

    public override async Task<Empty> AddItem(AddItemRequest request, ServerCallContext context)
    {
        _logger.LogInformation("AddItem called: userId={UserId}, productId={ProductId}, qty={Qty}",
            request.UserId, request.Item.ProductId, request.Item.Quantity);

        await _agent.AddItemAsync(request.UserId, request.Item.ProductId, request.Item.Quantity);
        return new Empty();
    }

    public override async Task<Cart> GetCart(GetCartRequest request, ServerCallContext context)
    {
        _logger.LogInformation("GetCart called: userId={UserId}", request.UserId);

        var items = await _agent.GetCartAsync(request.UserId);
        var cart = new Cart { UserId = request.UserId };
        cart.Items.AddRange(items);
        return cart;
    }

    public override async Task<Empty> EmptyCart(EmptyCartRequest request, ServerCallContext context)
    {
        _logger.LogInformation("EmptyCart called: userId={UserId}", request.UserId);

        await _agent.EmptyCartAsync(request.UserId);
        return new Empty();
    }
}
